"""Product model tool placeholder."""

from typing import Any

from app.models.common import DelegatedPrincipal
from app.models.session import SessionContext
from app.models.tools import ToolCallResponse
from app.tools.base import BaseTool


class ProductModelTool(BaseTool):
    """Tool contract for product model lookups through VAM backend APIs."""

    name = "product_model"
    description = "Access scoped product model information through the Python service boundary."
    required_permissions = ["product_model:read"]

    async def execute(
        self,
        *,
        session: SessionContext,
        principal: DelegatedPrincipal,
        arguments: dict[str, Any],
    ) -> ToolCallResponse:
        """Return a placeholder until VAM product model API contracts are implemented."""
        return ToolCallResponse(
            tool_name=self.name,
            status="not_implemented",
            result={"message": "Product model backend integration is not implemented yet."},
        )
