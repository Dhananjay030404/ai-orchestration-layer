"""Session lifecycle service for the secure Python runtime."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from time import perf_counter
from typing import Any
from uuid import uuid4

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    AppException,
    AuthorizationError,
    SessionClosedError,
    SessionExpiredError,
    VendorIntegrationError,
)
from app.models.elevenlabs import (
    ElevenLabsConversationSession,
    ElevenLabsConversationSessionRequest,
)
from app.models.session import (
    RuntimeSession,
    RuntimeSessionCreateRequest,
    RuntimeSessionStatus,
    RuntimeToolClaims,
    SessionChannel,
    SessionContext,
    UserContext,
    ValidatedAssistantClaims,
)
from app.repositories.session_repository import SessionRepository
from app.services.audit_service import AuditService
from app.services.elevenlabs_service import ElevenLabsService


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RuntimeSessionBootstrapResult:
    """Result of creating a runtime session and optional provider session."""

    runtime_session: RuntimeSession
    elevenlabs_session: ElevenLabsConversationSession | None = None


class SessionService:
    """Manage trusted Python runtime sessions."""

    def __init__(
        self,
        repository: SessionRepository,
        settings: Settings | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self.repository = repository
        self.settings = settings or get_settings()
        self.audit_service = audit_service or AuditService()

    async def create_runtime_session(
        self,
        request: RuntimeSessionCreateRequest,
    ) -> RuntimeSession:
        """Create a runtime session from already-validated assistant claims."""
        started_at = perf_counter()
        now = datetime.now(timezone.utc)
        ttl_expiry = now + timedelta(seconds=self.settings.session_ttl_seconds)
        expires_at = min(ttl_expiry, request.claims.expires_at)
        user_context = self._build_user_context(request.claims)

        session = RuntimeSession(
            runtime_session_id=str(uuid4()),
            assistant_session_id=request.claims.session_id,
            customer_id=user_context.customer_id,
            delegated_assistant_token=request.delegated_assistant_token,
            scope_mode=user_context.scope_mode,
            allowed_manufacturer_ids=user_context.allowed_manufacturer_ids,
            assistant_scopes=user_context.assistant_scopes,
            expires_at=expires_at,
            created_at=now,
            updated_at=now,
            status=RuntimeSessionStatus.ACTIVE,
            channel=request.channel,
            agent_id=request.agent_id,
            metadata=request.metadata,
        )
        await self.repository.save(session)
        logger.info(
            "runtime_session.created",
            extra={
                "sessionId": session.runtime_session_id,
                "assistantSessionId": session.assistant_session_id,
                "customerId": session.customer_id,
                "channel": session.channel.value,
                "durationMs": self._elapsed_ms(started_at),
            },
        )
        return session

    @staticmethod
    def _build_user_context(claims: ValidatedAssistantClaims) -> UserContext:
        """Build trusted runtime context from already-validated backend claims."""
        return UserContext(
            customer_id=claims.customer_id,
            scope_mode=claims.scope_mode,
            allowed_manufacturer_ids=claims.allowed_manufacturer_ids,
            assistant_scopes=claims.assistant_scopes,
        )

    async def bootstrap_runtime_session(
        self,
        request: RuntimeSessionCreateRequest,
        *,
        elevenlabs_service: ElevenLabsService | None = None,
    ) -> RuntimeSessionBootstrapResult:
        """Create a runtime session and initialize provider runtime state when requested."""
        started_at = perf_counter()
        session = await self.create_runtime_session(request)
        if not request.initialize_elevenlabs:
            return RuntimeSessionBootstrapResult(runtime_session=session)

        provider = elevenlabs_service or ElevenLabsService(settings=self.settings)
        try:
            elevenlabs_session = await provider.initialize_conversation_session(
                ElevenLabsConversationSessionRequest(
                    runtime_session_id=session.runtime_session_id,
                    agent_id=session.agent_id,
                )
            )
            updated_session = await self.attach_elevenlabs_conversation(
                session.runtime_session_id,
                elevenlabs_session.conversation_id,
                agent_id=elevenlabs_session.agent_id,
            )
            await self._record_audit_event(
                "runtime_session.elevenlabs.initialized",
                {
                    "runtime_session_id": updated_session.runtime_session_id,
                    "assistant_session_id": updated_session.assistant_session_id,
                    "agent_id": elevenlabs_session.agent_id,
                },
            )
            logger.info(
                "runtime_session.elevenlabs.initialized",
                extra={
                    "sessionId": updated_session.runtime_session_id,
                    "assistantSessionId": updated_session.assistant_session_id,
                    "agentId": elevenlabs_session.agent_id,
                    "durationMs": self._elapsed_ms(started_at),
                },
            )
            return RuntimeSessionBootstrapResult(
                runtime_session=updated_session,
                elevenlabs_session=elevenlabs_session,
            )
        except Exception as exc:
            await self.repository.delete(session.runtime_session_id)
            logger.exception(
                "Failed to initialize ElevenLabs runtime session",
                extra={
                    "sessionId": session.runtime_session_id,
                    "durationMs": self._elapsed_ms(started_at),
                },
            )
            await self._record_audit_event(
                "runtime_session.elevenlabs.initialization_failed",
                {
                    "runtime_session_id": session.runtime_session_id,
                    "assistant_session_id": session.assistant_session_id,
                    "error_type": type(exc).__name__,
                },
            )
            if isinstance(exc, AppException):
                raise
            raise VendorIntegrationError("ElevenLabs conversation initialization failed.") from exc

    @staticmethod
    def _elapsed_ms(started_at: float) -> float:
        return round((perf_counter() - started_at) * 1000, 2)

    async def _record_audit_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Record an audit event without letting audit failures affect session state."""
        try:
            await self.audit_service.record_event(event_type, payload)
        except Exception:
            logger.warning("Failed to record audit event", extra={"event_type": event_type})

    async def get_runtime_session(self, runtime_session_id: str) -> RuntimeSession:
        """Return an active runtime session by id."""
        session = await self.repository.get(runtime_session_id)
        return await self.assert_session_active(session)

    async def assert_session_active(self, session: RuntimeSession) -> RuntimeSession:
        """Reject expired or closed sessions before runtime work."""
        now = datetime.now(timezone.utc)
        if session.status == RuntimeSessionStatus.CLOSED:
            raise SessionClosedError()

        if session.expires_at <= now or session.status == RuntimeSessionStatus.EXPIRED:
            expired = session.model_copy(
                update={"status": RuntimeSessionStatus.EXPIRED, "updated_at": now}
            )
            await self.repository.save(expired)
            raise SessionExpiredError()

        return session

    async def update_runtime_session(self, session: RuntimeSession) -> RuntimeSession:
        """Persist an updated runtime session."""
        updated = session.model_copy(update={"updated_at": datetime.now(timezone.utc)})
        await self.repository.save(updated)
        return updated

    async def attach_elevenlabs_conversation(
        self,
        runtime_session_id: str,
        conversation_id: str,
        agent_id: str | None = None,
    ) -> RuntimeSession:
        """Attach an ElevenLabs conversation id to an active runtime session."""
        if not conversation_id.strip():
            raise ValueError("conversation_id is required.")

        session = await self.get_runtime_session(runtime_session_id)
        updates = {"elevenlabs_conversation_id": conversation_id.strip()}
        if agent_id and agent_id.strip():
            updates["agent_id"] = agent_id.strip()

        return await self.update_runtime_session(session.model_copy(update=updates))

    async def close_runtime_session(self, runtime_session_id: str) -> RuntimeSession:
        """Close a runtime session."""
        session = await self.repository.get(runtime_session_id)
        closed = session.model_copy(
            update={
                "status": RuntimeSessionStatus.CLOSED,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        await self.repository.save(closed)
        return closed

    async def cleanup_expired_sessions(self) -> int:
        """Mark expired sessions as expired and return the number touched."""
        now = datetime.now(timezone.utc)
        expired_sessions = await self.repository.list_expired(now)
        touched_count = 0
        for session in expired_sessions:
            if session.status in {RuntimeSessionStatus.CLOSED, RuntimeSessionStatus.EXPIRED}:
                continue

            await self.repository.save(
                session.model_copy(
                    update={"status": RuntimeSessionStatus.EXPIRED, "updated_at": now}
                )
            )
            touched_count += 1

        return touched_count

    async def get_session(self, session_id: str) -> SessionContext:
        """Compatibility wrapper for existing routes."""
        return await self.get_runtime_session(session_id)

    async def get_session_for_runtime_tool_token(
        self,
        session_id: str,
        claims: RuntimeToolClaims,
    ) -> SessionContext:
        """Return a session only when the Python-issued runtime tool token matches it."""
        if session_id != claims.runtime_session_id:
            raise AuthorizationError("The runtime tool token does not match this request.")

        session = await self.get_session(session_id)
        if (
            session.assistant_session_id != claims.assistant_session_id
            or session.customer_id != claims.customer_id
        ):
            raise AuthorizationError("The runtime tool token does not match this session.")

        return session
