"""Session routes for delegated assistant runtime setup."""

from fastapi import APIRouter, Depends, status

from app.models.session import SessionCreateRequest, SessionCreateResponse, SessionStatusResponse
from app.repositories.session_repository import session_repository
from app.services.session_service import SessionService
from app.services.token_validation_service import TokenValidationService


router = APIRouter(prefix="/sessions", tags=["sessions"])


def get_session_service() -> SessionService:
    """Provide the session service dependency."""
    return SessionService(repository=session_repository)


def get_token_validation_service() -> TokenValidationService:
    """Provide the delegated token validation dependency."""
    return TokenValidationService()


@router.post("", response_model=SessionCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: SessionCreateRequest,
    session_service: SessionService = Depends(get_session_service),
    token_service: TokenValidationService = Depends(get_token_validation_service),
) -> SessionCreateResponse:
    """Create an orchestration session from a delegated assistant token."""
    principal = await token_service.validate_delegated_token(payload.delegated_assistant_token)
    session = await session_service.create_session(principal=principal, metadata=payload.metadata)
    return SessionCreateResponse(
        session_id=session.session_id,
        status="created",
        expires_at=session.expires_at,
        elevenlabs_conversation_id=session.elevenlabs_conversation_id,
    )


@router.get("/{session_id}", response_model=SessionStatusResponse)
async def get_session(
    session_id: str,
    session_service: SessionService = Depends(get_session_service),
) -> SessionStatusResponse:
    """Return current session state without exposing raw delegated tokens."""
    session = await session_service.get_session(session_id)
    return SessionStatusResponse(
        session_id=session.session_id,
        status=session.status,
        created_at=session.created_at,
        expires_at=session.expires_at,
        elevenlabs_conversation_id=session.elevenlabs_conversation_id,
    )
