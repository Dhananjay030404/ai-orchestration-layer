"""Runtime tool execution service."""

import logging
from time import perf_counter

from app.core.exceptions import AppException
from app.models.session import RuntimeSession, RuntimeToolClaims
from app.models.tools import ToolExecutionRequest, ToolExecutionResponse
from app.services.authorization_service import AuthorizationService
from app.services.session_service import SessionService
from app.tools.registry import ToolRegistry, tool_registry


logger = logging.getLogger(__name__)


class ToolExecutionService:
    """Coordinate trusted session loading, authorization, and tool dispatch."""

    def __init__(
        self,
        *,
        session_service: SessionService,
        authorization_service: AuthorizationService | None = None,
        registry: ToolRegistry | None = None,
    ) -> None:
        self.session_service = session_service
        self.authorization_service = authorization_service or AuthorizationService()
        self.registry = registry or tool_registry

    async def execute_for_runtime_tool_token(
        self,
        request: ToolExecutionRequest,
        claims: RuntimeToolClaims,
    ) -> ToolExecutionResponse:
        """Execute a tool for a Python-issued runtime tool token."""
        started_at = perf_counter()
        logger.info(
            "runtime_tool.execute.start",
            extra={
                "sessionId": request.session_id,
                "toolName": request.tool_name,
                "outcome": "started",
                "authMode": "runtime_tool_token",
            },
        )

        try:
            session = await self.session_service.get_session_for_runtime_tool_token(
                request.session_id,
                claims,
            )
            response = await self._execute_for_active_session(request, session)
        except AppException as exc:
            logger.warning(
                "runtime_tool.execute.rejected",
                extra={
                    "sessionId": request.session_id,
                    "toolName": request.tool_name,
                    "durationMs": self._elapsed_ms(started_at),
                    "outcome": exc.code,
                    "authMode": "runtime_tool_token",
                },
            )
            raise
        except Exception:
            logger.exception(
                "runtime_tool.execute.failed",
                extra={
                    "sessionId": request.session_id,
                    "toolName": request.tool_name,
                    "durationMs": self._elapsed_ms(started_at),
                    "outcome": "failed",
                    "authMode": "runtime_tool_token",
                },
            )
            raise

        logger.info(
            "runtime_tool.execute.completed",
            extra={
                "sessionId": request.session_id,
                "toolName": request.tool_name,
                "durationMs": self._elapsed_ms(started_at),
                "outcome": response.status.value,
                "authMode": "runtime_tool_token",
            },
        )
        return response

    async def execute_for_session(
        self,
        request: ToolExecutionRequest,
        session: RuntimeSession,
    ) -> ToolExecutionResponse:
        """Execute a tool for a trusted active runtime session."""
        active_session = await self.session_service.assert_session_active(session)
        return await self._execute_for_active_session(request, active_session)

    async def _execute_for_active_session(
        self,
        request: ToolExecutionRequest,
        session: RuntimeSession,
    ) -> ToolExecutionResponse:
        auth_context = self.authorization_service.build_tool_authorization_context(session)
        return await self.registry.execute(
            request,
            auth_context,
            runtime_session=session,
            authorization_service=self.authorization_service,
        )

    @staticmethod
    def _elapsed_ms(started_at: float) -> float:
        return round((perf_counter() - started_at) * 1000, 2)
