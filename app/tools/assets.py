"""Assets tool placeholder."""

from typing import Any

from app.models.common import DelegatedPrincipal
from app.models.session import SessionContext
from app.models.tools import ToolCallResponse
from app.tools.base import BaseTool


class AssetsTool(BaseTool):
    """Tool contract for asset lookups through VAM backend APIs."""

    name = "assets"
    description = "Access scoped asset information through the Python service boundary."
    required_permissions = ["assets:read"]

    async def execute(
        self,
        *,
        session: SessionContext,
        principal: DelegatedPrincipal,
        arguments: dict[str, Any],
    ) -> ToolCallResponse:
        """Return a placeholder until VAM asset API contracts are implemented."""
        return ToolCallResponse(
            tool_name=self.name,
            status="not_implemented",
            result={"message": "Assets backend integration is not implemented yet."},
        )
