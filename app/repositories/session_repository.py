"""Session persistence abstraction."""

from typing import Protocol

from app.core.exceptions import NotFoundError
from app.models.session import SessionContext


class SessionRepository(Protocol):
    """Persistence contract for session storage."""

    async def save(self, session: SessionContext) -> None:
        """Persist a session."""

    async def get(self, session_id: str) -> SessionContext:
        """Return a session by id."""


class InMemorySessionRepository:
    """Development repository for sessions.

    TODO: Replace with Redis or another durable store for horizontally scaled deployments.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, SessionContext] = {}

    async def save(self, session: SessionContext) -> None:
        """Persist a session in process memory."""
        self._sessions[session.session_id] = session

    async def get(self, session_id: str) -> SessionContext:
        """Return a session by id."""
        session = self._sessions.get(session_id)
        if session is None:
            raise NotFoundError("session", session_id)
        return session


session_repository = InMemorySessionRepository()
