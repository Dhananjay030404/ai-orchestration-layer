"""Session persistence abstraction."""

import asyncio
from datetime import datetime
from typing import Any, Protocol

from app.core.config import Settings
from app.core.config import get_settings
from app.core.exceptions import ConfigurationError, SessionNotFoundError
from app.models.session import RuntimeSession


class SessionRepository(Protocol):
    """Persistence contract for runtime session storage."""

    async def save(self, session: RuntimeSession) -> None:
        """Persist a runtime session."""

    async def get(self, runtime_session_id: str) -> RuntimeSession:
        """Return a runtime session by id."""

    async def delete(self, runtime_session_id: str) -> None:
        """Delete a runtime session by id."""

    async def list_expired(self, now: datetime) -> list[RuntimeSession]:
        """Return sessions whose expiration time has passed."""


class InMemorySessionRepository:
    """Unit-test repository for sessions.

    The configured application repository is MySQL. This test double stays here
    so service-level tests can avoid external infrastructure.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, RuntimeSession] = {}

    async def save(self, session: RuntimeSession) -> None:
        """Persist a runtime session in process memory."""
        self._sessions[session.runtime_session_id] = session

    async def get(self, runtime_session_id: str) -> RuntimeSession:
        """Return a runtime session by id."""
        session = self._sessions.get(runtime_session_id)
        if session is None:
            raise SessionNotFoundError(details={"runtime_session_id": runtime_session_id})
        return session

    async def delete(self, runtime_session_id: str) -> None:
        """Delete a runtime session by id."""
        self._sessions.pop(runtime_session_id, None)

    async def list_expired(self, now: datetime) -> list[RuntimeSession]:
        """Return sessions whose expiration time has passed."""
        return [session for session in self._sessions.values() if session.expires_at <= now]

    async def ping(self) -> None:
        """No-op health check for unit tests."""
        return None


class MySQLSessionRepository:
    """Durable shared session repository backed by MySQL."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        pool_min_size: int,
        pool_max_size: int,
        connect_timeout_seconds: float,
    ) -> None:
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.pool_min_size = pool_min_size
        self.pool_max_size = pool_max_size
        self.connect_timeout_seconds = connect_timeout_seconds
        self._pool = None
        self._pool_lock = asyncio.Lock()

    async def save(self, session: RuntimeSession) -> None:
        """Persist a runtime session in MySQL."""
        pool = await self._get_pool()
        async with pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    """
                    INSERT INTO assistant_runtime_sessions (
                        runtime_session_id,
                        assistant_session_id,
                        customer_id,
                        status,
                        expires_at,
                        payload_json,
                        created_at,
                        updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        assistant_session_id = VALUES(assistant_session_id),
                        customer_id = VALUES(customer_id),
                        status = VALUES(status),
                        expires_at = VALUES(expires_at),
                        payload_json = VALUES(payload_json),
                        updated_at = VALUES(updated_at)
                    """,
                    (
                        session.runtime_session_id,
                        session.assistant_session_id,
                        session.customer_id,
                        session.status.value,
                        session.expires_at.replace(tzinfo=None),
                        session.model_dump_json(),
                        session.created_at.replace(tzinfo=None),
                        session.updated_at.replace(tzinfo=None),
                    ),
                )

    async def get(self, runtime_session_id: str) -> RuntimeSession:
        """Return a runtime session by id."""
        pool = await self._get_pool()
        async with pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT payload_json
                    FROM assistant_runtime_sessions
                    WHERE runtime_session_id = %s
                    """,
                    (runtime_session_id,),
                )
                row = await cursor.fetchone()

        if row is None:
            raise SessionNotFoundError(details={"runtime_session_id": runtime_session_id})

        return RuntimeSession.model_validate_json(str(row[0]))

    async def delete(self, runtime_session_id: str) -> None:
        """Delete a runtime session by id."""
        pool = await self._get_pool()
        async with pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "DELETE FROM assistant_runtime_sessions WHERE runtime_session_id = %s",
                    (runtime_session_id,),
                )

    async def list_expired(self, now: datetime) -> list[RuntimeSession]:
        """Return sessions whose expiration time has passed."""
        pool = await self._get_pool()
        async with pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT payload_json
                    FROM assistant_runtime_sessions
                    WHERE expires_at <= %s
                    """,
                    (now.replace(tzinfo=None),),
                )
                rows = await cursor.fetchall()

        return [RuntimeSession.model_validate_json(str(row[0])) for row in rows]

    async def close(self) -> None:
        """Close the MySQL connection pool."""
        if self._pool is None:
            return
        self._pool.close()
        await self._pool.wait_closed()
        self._pool = None

    async def _get_pool(self) -> Any:
        if self._pool is not None:
            return self._pool

        async with self._pool_lock:
            if self._pool is not None:
                return self._pool

            try:
                import asyncmy
            except ImportError as exc:
                raise ConfigurationError(
                    message="MySQL session repository requires the asyncmy package.",
                    details={"package": "asyncmy"},
                ) from exc

            self._pool = await asyncmy.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                db=self.database,
                minsize=self.pool_min_size,
                maxsize=self.pool_max_size,
                connect_timeout=self.connect_timeout_seconds,
                autocommit=True,
            )
            await self._ensure_schema()
            return self._pool

    async def _ensure_schema(self) -> None:
        pool = self._pool
        if pool is None:
            return

        async with pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS assistant_runtime_sessions (
                        runtime_session_id VARCHAR(64) PRIMARY KEY,
                        assistant_session_id VARCHAR(128) NOT NULL,
                        customer_id VARCHAR(64) NOT NULL,
                        status VARCHAR(32) NOT NULL,
                        expires_at DATETIME(6) NOT NULL,
                        payload_json LONGTEXT NOT NULL,
                        created_at DATETIME(6) NOT NULL,
                        updated_at DATETIME(6) NOT NULL,
                        INDEX idx_assistant_runtime_sessions_expires_at (expires_at),
                        INDEX idx_assistant_runtime_sessions_customer_id (customer_id),
                        INDEX idx_assistant_runtime_sessions_assistant_session_id (assistant_session_id)
                    )
                    """
                )

    async def initialize(self) -> None:
        """Open the pool and verify the schema is ready."""
        await self._get_pool()

    async def ping(self) -> None:
        """Verify MySQL is reachable."""
        pool = await self._get_pool()
        async with pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute("SELECT 1")

def _build_mysql_repository(settings: Settings) -> MySQLSessionRepository:
    missing_fields = [
        field_name
        for field_name, value in {
            "MYSQL_HOST": settings.mysql_host,
            "MYSQL_DATABASE": settings.mysql_database,
            "MYSQL_USER": settings.mysql_user,
            "MYSQL_PASSWORD": settings.mysql_password,
        }.items()
        if value is None
    ]
    if missing_fields:
        raise ConfigurationError(
            message="MySQL session repository is not fully configured.",
            details={"missing_fields": missing_fields},
        )

    return MySQLSessionRepository(
        host=str(settings.mysql_host),
        port=settings.mysql_port,
        database=str(settings.mysql_database),
        user=str(settings.mysql_user),
        password=str(settings.mysql_password),
        pool_min_size=settings.mysql_pool_min_size,
        pool_max_size=settings.mysql_pool_max_size,
        connect_timeout_seconds=settings.mysql_connect_timeout_seconds,
    )


def build_session_repository() -> SessionRepository:
    """Build the configured session repository."""
    settings = get_settings()
    backend = settings.session_repository_backend.strip().lower()
    if backend == "mysql":
        return _build_mysql_repository(settings)
    raise ConfigurationError(
        message="Unsupported session repository backend.",
        details={"backend": settings.session_repository_backend, "supported_backends": ["mysql"]},
    )


async def close_session_repository(repository: SessionRepository | None = None) -> None:
    """Close repository resources when the implementation owns any."""
    target = repository or session_repository
    close = getattr(target, "close", None)
    if close is not None:
        await close()


async def initialize_session_repository(repository: SessionRepository | None = None) -> None:
    """Initialize repository resources and fail startup when persistence is unavailable."""
    target = repository or session_repository
    initialize = getattr(target, "initialize", None)
    if initialize is not None:
        await initialize()


async def check_session_repository(repository: SessionRepository | None = None) -> None:
    """Verify repository dependencies are healthy."""
    target = repository or session_repository
    ping = getattr(target, "ping", None)
    if ping is not None:
        await ping()


session_repository = build_session_repository()
