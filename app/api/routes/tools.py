"""Tool routes that keep business operations inside the Python runtime boundary."""

from fastapi import APIRouter, Depends

from app.core.security import require_delegated_token
from app.models.tools import ToolExecutionRequest, ToolExecutionResponse
from app.repositories.session_repository import session_repository
from app.services.authorization_service import AuthorizationService
from app.services.session_service import SessionService
from app.services.token_validation_service import TokenValidationService
from app.services.tool_execution_service import ToolExecutionService
from app.tools.registry import tool_registry


assistant_runtime_router = APIRouter(prefix="/assistant/runtime/tools", tags=["assistant-runtime-tools"])


async def get_session_service() -> SessionService:
    """Provide the session service dependency."""
    return SessionService(repository=session_repository)


async def get_token_validation_service() -> TokenValidationService:
    """Provide the delegated token validation service dependency."""
    return TokenValidationService()


async def get_tool_execution_service(
    session_service: SessionService = Depends(get_session_service),
) -> ToolExecutionService:
    """Provide the runtime tool execution service dependency."""
    return ToolExecutionService(
        session_service=session_service,
        authorization_service=AuthorizationService(),
        registry=tool_registry,
    )


@assistant_runtime_router.post(
    "/execute",
    response_model=ToolExecutionResponse,
    response_model_by_alias=True,
)
async def execute_runtime_tool(
    payload: ToolExecutionRequest,
    bearer_token: str = Depends(require_delegated_token),
    token_service: TokenValidationService = Depends(get_token_validation_service),
    execution_service: ToolExecutionService = Depends(get_tool_execution_service),
) -> ToolExecutionResponse:
    """Execute a runtime tool request from a trusted assistant runtime flow."""
    claims = await token_service.validate_runtime_tool_token(bearer_token)
    return await execution_service.execute_for_runtime_tool_token(payload, claims)
