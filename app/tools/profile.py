"""Profile tool placeholder."""

from typing import Any

from app.models.session import SessionContext, ValidatedAssistantClaims
from app.models.tools import ToolCallResponse
from app.tools.base import BaseTool


class ProfileTool(BaseTool):
    """Tool contract for profile lookups through VAM backend APIs."""

    name = "profile"
    description = "Access customer profile information through the Python service boundary."
    required_permissions = ["profile:read"]

    async def execute(
        self,
        *,
        session: SessionContext,
        principal: ValidatedAssistantClaims,
        arguments: dict[str, Any],
    ) -> ToolCallResponse:
        """Return a placeholder until VAM profile API contracts are implemented."""
        return ToolCallResponse(
            tool_name=self.name,
            status="not_implemented",
            result={"message": "Profile backend integration is not implemented yet."},
        )
