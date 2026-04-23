"""Registry for all tools exposed to the ElevenLabs runtime through Python."""

from app.core.exceptions import NotFoundError
from app.models.tools import ToolDefinition
from app.tools.assets import AssetsTool
from app.tools.base import BaseTool
from app.tools.manuals import ManualsTool
from app.tools.product_model import ProductModelTool
from app.tools.profile import ProfileTool


class ToolRegistry:
    """In-memory registry for tool contracts."""

    def __init__(self, tools: list[BaseTool]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    def list_definitions(self) -> list[ToolDefinition]:
        """Return registered tool definitions."""
        return [tool.definition() for tool in self._tools.values()]

    def get(self, name: str) -> BaseTool:
        """Return a registered tool by name."""
        tool = self._tools.get(name)
        if tool is None:
            raise NotFoundError("tool", name)
        return tool


tool_registry = ToolRegistry(
    tools=[
        ProfileTool(),
        AssetsTool(),
        ManualsTool(),
        ProductModelTool(),
    ]
)
