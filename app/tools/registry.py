"""Registry for tools exposed through the Python runtime boundary."""

from app.core.exceptions import UnknownToolError
from app.models.tools import (
    AssistantScope,
    ManufacturerScopeRequirement,
    ToolAuthorizationContext,
    ToolDefinitionMetadata,
    ToolExecutionRequest,
    ToolExecutionResponse,
)
from app.models.session import RuntimeSession
from app.services.authorization_service import AuthorizationService
from app.tools.base import BaseTool
from app.tools.assets import CustomerAssetTool
from app.tools.profile import ProfileReadTool


class ToolRegistry:
    """In-memory registry for assistant tool contracts."""

    def __init__(self, tools: list[BaseTool] | None = None) -> None:
        self._tools: dict[str, BaseTool] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: BaseTool) -> None:
        """Register a tool contract."""
        if tool.name in self._tools:
            raise ValueError(f"Tool is already registered: {tool.name}")
        self._tools[tool.name] = tool

    def resolve(self, name: str) -> BaseTool:
        """Return a registered tool by name."""
        tool = self._tools.get(name)
        if tool is None:
            raise UnknownToolError(details={"tool_name": name})
        return tool

    def get(self, name: str) -> BaseTool:
        """Compatibility alias for earlier callers."""
        return self.resolve(name)

    def list_available(self) -> list[ToolDefinitionMetadata]:
        """Return all registered tool definitions."""
        return [tool.definition() for tool in self._tools.values()]

    def list_definitions(self) -> list[ToolDefinitionMetadata]:
        """Compatibility alias for earlier callers."""
        return self.list_available()

    async def execute(
        self,
        request: ToolExecutionRequest,
        auth_context: ToolAuthorizationContext,
        runtime_session: RuntimeSession,
        authorization_service: AuthorizationService | None = None,
    ) -> ToolExecutionResponse:
        """Validate, authorize, and execute a registered tool."""
        authorization = authorization_service or AuthorizationService()
        tool = self.resolve(request.tool_name)
        input_payload = tool.validate_input(request.input)

        authorization.require_scope(auth_context, tool.required_scope)
        authorization.validate_manufacturer_access(
            auth_context,
            tool.manufacturer_scope,
            AuthorizationService.manufacturer_id_from_input(input_payload),
        )

        return await tool.execute(
            input_payload=input_payload,
            auth_context=auth_context,
            runtime_session=runtime_session,
        )


tool_registry = ToolRegistry(
    tools=[
        ProfileReadTool(),
        CustomerAssetTool(),
    ]
)
