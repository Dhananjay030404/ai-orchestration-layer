"""Manuals tool placeholder."""

from typing import Any

from app.models.session import SessionContext, ValidatedAssistantClaims
from app.models.tools import ToolCallResponse
from app.tools.base import BaseTool


class ManualsTool(BaseTool):
    """Tool contract for manual retrieval through VAM backend APIs."""

    name = "manuals"
    description = "Access scoped manual information through the Python service boundary."
    required_permissions = ["manuals:read"]

    async def execute(
        self,
        *,
        session: SessionContext,
        principal: ValidatedAssistantClaims,
        arguments: dict[str, Any],
    ) -> ToolCallResponse:
        """Return a placeholder until VAM manuals API contracts are implemented."""
        return ToolCallResponse(
            tool_name=self.name,
            status="not_implemented",
            result={"message": "Manuals backend integration is not implemented yet."},
        )
