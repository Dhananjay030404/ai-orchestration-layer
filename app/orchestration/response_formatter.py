"""Response formatting helpers for runtime and tool outputs."""

from app.models.tools import ToolCallResponse


class ResponseFormatter:
    """Normalize orchestration responses before returning them to runtimes."""

    def format_tool_response(self, response: ToolCallResponse) -> dict:
        """Return a provider-neutral tool response payload."""
        return response.model_dump()
