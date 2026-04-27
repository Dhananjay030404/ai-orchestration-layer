"""Session lifecycle service for the secure Python runtime."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.core.config import Settings, get_settings
from app.core.exceptions import AuthorizationError
from typing import Any

from app.models.session import SessionContext, ValidatedAssistantClaims
from app.repositories.session_repository import SessionRepository


class SessionService:
    """Create and retrieve orchestration sessions."""

    def __init__(self, repository: SessionRepository, settings: Settings | None = None) -> None:
        self.repository = repository
        self.settings = settings or get_settings()

    async def create_session(
        self,
        principal: ValidatedAssistantClaims,
        metadata: dict[str, Any],
    ) -> SessionContext:
        """Create a session scoped to the validated delegated principal."""
        now = datetime.now(timezone.utc)
        ttl_expiry = now + timedelta(seconds=self.settings.session_ttl_seconds)
        expires_at = min(ttl_expiry, principal.expires_at) if principal.expires_at else ttl_expiry

        session = SessionContext(
            session_id=str(uuid4()),
            principal=principal,
            created_at=now,
            expires_at=expires_at,
            metadata=metadata,
        )
        await self.repository.save(session)
        return session

    async def get_session(self, session_id: str) -> SessionContext:
        """Return a session by id, raising if it does not exist."""
        return await self.repository.get(session_id)

    async def get_session_for_principal(
        self,
        session_id: str,
        principal: ValidatedAssistantClaims,
    ) -> SessionContext:
        """Return a session only when the current token matches its trusted principal."""
        session = await self.get_session(session_id)
        if (
            session.principal.subject != principal.subject
            or session.principal.customer_id != principal.customer_id
            or session.principal.manufacturer_id != principal.manufacturer_id
        ):
            raise AuthorizationError("The delegated principal does not match this session.")

        if session.expires_at <= datetime.now(timezone.utc):
            raise AuthorizationError("The orchestration session has expired.")

        return session
