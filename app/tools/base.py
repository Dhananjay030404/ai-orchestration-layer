"""Base contracts for Python-mediated tools."""

from abc import ABC, abstractmethod
from typing import Any

from app.models.common import DelegatedPrincipal
from app.models.session import SessionContext
from app.models.tools import ToolCallResponse, ToolDefinition


class BaseTool(ABC):
    """Base class for all business tools."""

    name: str
    description: str
    required_permissions: list[str] = []

    def definition(self) -> ToolDefinition:
        """Return the public tool contract."""
        return ToolDefinition(
            name=self.name,
            description=self.description,
            required_permissions=self.required_permissions,
        )

    @abstractmethod
    async def execute(
        self,
        *,
        session: SessionContext,
        principal: DelegatedPrincipal,
        arguments: dict[str, Any],
    ) -> ToolCallResponse:
        """Execute the tool after token, session, and permission checks pass."""
