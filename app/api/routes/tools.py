"""Tool routes that keep business operations inside the Python runtime boundary."""

from fastapi import APIRouter, Depends

from app.core.security import require_delegated_token
from app.models.tools import ToolCallRequest, ToolCallResponse, ToolDefinition
from app.repositories.session_repository import session_repository
from app.services.authorization_service import AuthorizationService
from app.services.session_service import SessionService
from app.services.token_validation_service import TokenValidationService
from app.tools.registry import tool_registry


router = APIRouter(prefix="/tools", tags=["tools"])


def get_session_service() -> SessionService:
    """Provide the session service dependency."""
    return SessionService(repository=session_repository)


@router.get("", response_model=list[ToolDefinition])
async def list_tools() -> list[ToolDefinition]:
    """List registered tool contracts without exposing implementation details."""
    return tool_registry.list_definitions()


@router.post("/call", response_model=ToolCallResponse)
async def call_tool(
    payload: ToolCallRequest,
    bearer_token: str = Depends(require_delegated_token),
    session_service: SessionService = Depends(get_session_service),
) -> ToolCallResponse:
    """Execute a registered tool after delegated token and session authorization."""
    principal = await TokenValidationService().validate_delegated_token(bearer_token)
    session = await session_service.get_session_for_principal(payload.session_id, principal)
    tool = tool_registry.get(payload.tool_name)

    AuthorizationService().require_permissions(principal, tool.required_permissions)
    return await tool.execute(session=session, principal=principal, arguments=payload.arguments)
