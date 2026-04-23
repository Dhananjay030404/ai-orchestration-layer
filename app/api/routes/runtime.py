"""Runtime routes for preparing conversation handoff to ElevenLabs."""

from fastapi import APIRouter, Depends

from app.core.security import require_delegated_token
from app.models.elevenlabs import ElevenLabsRuntimeConfig
from app.repositories.session_repository import session_repository
from app.services.elevenlabs_service import ElevenLabsService
from app.services.session_service import SessionService
from app.services.token_validation_service import TokenValidationService


router = APIRouter(prefix="/runtime", tags=["runtime"])


def get_session_service() -> SessionService:
    """Provide the session service dependency."""
    return SessionService(repository=session_repository)


@router.post("/sessions/{session_id}/prepare", response_model=ElevenLabsRuntimeConfig)
async def prepare_runtime(
    session_id: str,
    bearer_token: str = Depends(require_delegated_token),
    session_service: SessionService = Depends(get_session_service),
) -> ElevenLabsRuntimeConfig:
    """Prepare runtime metadata for ElevenLabs without making ElevenLabs authoritative."""
    principal = await TokenValidationService().validate_delegated_token(bearer_token)
    session = await session_service.get_session_for_principal(session_id, principal)
    return await ElevenLabsService().prepare_runtime_session(session)
