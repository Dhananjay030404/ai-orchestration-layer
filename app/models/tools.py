"""Tool contract models for Python-mediated business actions."""

from enum import Enum
from typing import Any

from pydantic import AliasChoices, Field

from app.models.common import ApiModel


class AssistantScope(str, Enum):
    """Assistant scopes issued by the VAM backend delegated token."""

    CUSTOMER_PROFILE_READ = "CUSTOMER_PROFILE_READ"
    CUSTOMER_ASSET_READ = "CUSTOMER_ASSET_READ"
    #CUSTOMER_ASSET_SEARCH = "CUSTOMER_ASSET_SEARCH"
  #  CUSTOMER_ASSET_DOCUMENT_READ = "CUSTOMER_ASSET_DOCUMENT_READ"
   # PRODUCT_MODEL_READ = "PRODUCT_MODEL_READ"


class ManufacturerScopeRequirement(str, Enum):
    """Manufacturer scoping requirements for a tool."""

    NONE = "none"
    OPTIONAL = "optional"
    REQUIRED = "required"


class ToolExecutionStatus(str, Enum):
    """Normalized tool execution states."""

    COMPLETED = "completed"
    NOT_IMPLEMENTED = "not_implemented"
    FAILED = "failed"


class ToolAuthorizationContext(ApiModel):
    """Trusted authorization context built from the runtime session."""

    runtime_session_id: str = Field(..., min_length=1)
    assistant_session_id: str = Field(..., min_length=1)
    customer_id: str = Field(..., min_length=1)
    scope_mode: str = Field(..., min_length=1)
    allowed_manufacturer_ids: list[str] = Field(default_factory=list)
    assistant_scopes: list[str] = Field(default_factory=list)


class ToolDefinitionMetadata(ApiModel):
    """Public metadata for a registered assistant tool."""

    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    required_scope: AssistantScope = Field(..., alias="requiredScope")
    input_schema: dict[str, Any] = Field(default_factory=dict, alias="inputSchema")
    authorization_rules: dict[str, Any] = Field(default_factory=dict, alias="authorizationRules")
    manufacturer_scope: ManufacturerScopeRequirement = Field(
        default=ManufacturerScopeRequirement.NONE,
        alias="manufacturerScope",
    )


class NormalizedToolPayload(ApiModel):
    """Normalized payload returned by a tool execution."""

    data: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolExecutionRequest(ApiModel):
    """Request to execute a registered tool for a trusted runtime session."""

    runtime_session_id: str = Field(
        ...,
        min_length=1,
        alias="runtimeSessionId",
        validation_alias=AliasChoices("runtimeSessionId", "runtime_session_id", "sessionId", "session_id"),
    )
    tool_name: str = Field(
        ...,
        min_length=1,
        alias="toolName",
        validation_alias=AliasChoices("toolName", "tool_name"),
    )
    input: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("input", "arguments", "parameters"),
    )

    @property
    def session_id(self) -> str:
        """Compatibility alias used by the existing tools route."""
        return self.runtime_session_id

    @property
    def arguments(self) -> dict[str, Any]:
        """Compatibility alias used by earlier tool contracts."""
        return self.input


class ToolExecutionResponse(ApiModel):
    """Normalized response returned by every assistant tool."""

    tool_name: str = Field(..., alias="toolName")
    status: ToolExecutionStatus
    result: dict[str, Any] = Field(default_factory=dict)
    payload: NormalizedToolPayload | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


ToolDefinition = ToolDefinitionMetadata
ToolCallRequest = ToolExecutionRequest
ToolCallResponse = ToolExecutionResponse
ToolStatus = ToolExecutionStatus
