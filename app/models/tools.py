"""Tool contract models for Python-mediated business actions."""

from typing import Any, Literal

from pydantic import Field

from app.models.common import ApiModel


ToolStatus = Literal["completed", "not_implemented", "failed"]


class ToolDefinition(ApiModel):
    """Public description of a registered tool contract."""

    name: str
    description: str
    required_permissions: list[str] = Field(default_factory=list)


class ToolCallRequest(ApiModel):
    """Request to execute a tool for a validated orchestration session."""

    session_id: str = Field(..., min_length=1)
    tool_name: str = Field(..., min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolCallResponse(ApiModel):
    """Response returned by a tool execution."""

    tool_name: str
    status: ToolStatus
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
