"""Session routes for delegated assistant runtime setup."""

from fastapi import APIRouter, Body, Depends, status

from app.core.security import require_delegated_token
from app.models.session import (
    RuntimeSessionBootstrapRequest,
    RuntimeSessionCreateRequest,
    RuntimeSessionCreateResponse,
    SessionChannel,
)
from app.repositories.session_repository import session_repository
from app.services.elevenlabs_service import ElevenLabsService
from app.services.session_service import SessionService
from app.services.token_validation_service import TokenValidationService


assistant_runtime_router = APIRouter(prefix="/assistant/runtime", tags=["assistant-runtime"])


async def get_session_service() -> SessionService:
    """Provide the session service dependency."""
    return SessionService(repository=session_repository)


async def get_token_validation_service() -> TokenValidationService:
    """Provide the delegated token validation dependency."""
    return TokenValidationService()


async def get_elevenlabs_service() -> ElevenLabsService:
    """Provide the ElevenLabs integration dependency."""
    return ElevenLabsService()


@assistant_runtime_router.post(
    "/session",
    response_model=RuntimeSessionCreateResponse,
    response_model_by_alias=True,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
async def create_runtime_session(
    payload: RuntimeSessionBootstrapRequest | None = Body(default=None),
    bearer_token: str = Depends(require_delegated_token),
    session_service: SessionService = Depends(get_session_service),
    token_service: TokenValidationService = Depends(get_token_validation_service),
    elevenlabs_service: ElevenLabsService = Depends(get_elevenlabs_service),
) -> RuntimeSessionCreateResponse:
    """Bootstrap a trusted ElevenLabs runtime session from a delegated assistant token."""
    bootstrap_payload = payload or RuntimeSessionBootstrapRequest()
    claims = await token_service.validate_assistant_token(bearer_token)
    bootstrap_result = await session_service.bootstrap_runtime_session(
        RuntimeSessionCreateRequest(
            claims=claims,
            delegated_assistant_token=bearer_token,
            channel=SessionChannel.ELEVENLABS,
            agent_id=bootstrap_payload.agent_id,
            initialize_elevenlabs=True,
        ),
        elevenlabs_service=elevenlabs_service,
    )
    runtime_session = bootstrap_result.runtime_session
    runtime_tool_token = token_service.mint_runtime_tool_token(runtime_session)
    return RuntimeSessionCreateResponse(
        runtime_session_id=runtime_session.runtime_session_id,
        assistant_session_id=runtime_session.assistant_session_id,
        expires_at=runtime_session.expires_at,
        status=runtime_session.status,
        channel=runtime_session.channel,
        agent_id=runtime_session.agent_id,
        elevenlabs_conversation_id=runtime_session.elevenlabs_conversation_id,
        elevenlabs_signed_url=(
            bootstrap_result.elevenlabs_session.signed_url
            if bootstrap_result.elevenlabs_session
            else None
        ),
        runtime_tool_token=runtime_tool_token,
        elevenlabs_dynamic_variables=build_elevenlabs_dynamic_variables(
            runtime_session.runtime_session_id,
            runtime_tool_token,
        ),
    )


def build_elevenlabs_dynamic_variables(
    runtime_session_id: str,
    runtime_tool_token: str,
) -> dict[str, str]:
    """Build values injected into the ElevenLabs conversation at startup."""
    return {
        "runtimeSessionId": runtime_session_id,
        "runtimeToolToken": runtime_tool_token,
        "runtimeToolAuthorization": f"Bearer {runtime_tool_token}",
    }
