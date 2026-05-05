"""Base contracts for Python-mediated assistant tools."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import BaseModel, ValidationError

from app.core.exceptions import InvalidToolInputError
from app.models.tools import (
    AssistantScope,
    ManufacturerScopeRequirement,
    NormalizedToolPayload,
    ToolAuthorizationContext,
    ToolDefinitionMetadata,
    ToolExecutionResponse,
    ToolExecutionStatus,
)

if TYPE_CHECKING:
    from app.models.session import RuntimeSession


class BaseTool(ABC):
    """Base class for registry-driven assistant tools."""

    name: ClassVar[str]
    description: ClassVar[str]
    required_scope: ClassVar[AssistantScope]
    input_schema: ClassVar[dict[str, Any]] = {"type": "object", "additionalProperties": True}
    input_model: ClassVar[type[BaseModel] | None] = None
    authorization_rules: ClassVar[dict[str, Any]] = {}
    manufacturer_scope: ClassVar[ManufacturerScopeRequirement] = ManufacturerScopeRequirement.NONE

    @property
    def required_permissions(self) -> list[str]:
        """Compatibility alias for earlier authorization code."""
        return [self.required_scope.value]

    def definition(self) -> ToolDefinitionMetadata:
        """Return public metadata for this tool."""
        return ToolDefinitionMetadata(
            name=self.name,
            description=self.description,
            required_scope=self.required_scope,
            input_schema=self.input_schema,
            authorization_rules=self.authorization_rules,
            manufacturer_scope=self.manufacturer_scope,
        )

    def validate_input(self, input_payload: dict[str, Any]) -> dict[str, Any]:
        """Validate and normalize tool input before execution."""
        if not isinstance(input_payload, dict):
            raise InvalidToolInputError("Tool input must be a JSON object.")

        if self.input_model is None:
            return input_payload

        try:
            model = self.input_model.model_validate(input_payload)
        except ValidationError as exc:
            raise InvalidToolInputError(
                "Tool input validation failed.",
                details={"errors": exc.errors()},
            ) from exc

        return model.model_dump()

    def format_output(
        self,
        result: dict[str, Any],
        *,
        status: ToolExecutionStatus = ToolExecutionStatus.COMPLETED,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ToolExecutionResponse:
        """Return the normalized response shape for this tool."""
        return ToolExecutionResponse(
            tool_name=self.name,
            status=status,
            result=result,
            payload=NormalizedToolPayload(data=result, metadata=metadata or {}),
            error=error,
            metadata=metadata or {},
        )

    @abstractmethod
    async def execute(
        self,
        *,
        input_payload: dict[str, Any],
        auth_context: ToolAuthorizationContext,
        runtime_session: "RuntimeSession",
    ) -> ToolExecutionResponse:
        """Execute the tool after input and authorization have been validated."""
