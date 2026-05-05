"""Authorization checks over trusted runtime session context."""

from typing import Any

from app.core.exceptions import (
    AuthorizationError,
    InvalidManufacturerAccessError,
    MissingToolScopeError,
)
from app.models.session import RuntimeSession, ValidatedAssistantClaims
from app.models.tools import (
    AssistantScope,
    ManufacturerScopeRequirement,
    ToolAuthorizationContext,
)


class AuthorizationService:
    """Evaluate assistant scopes issued by the VAM backend."""

    def build_tool_authorization_context(
        self,
        session: RuntimeSession,
    ) -> ToolAuthorizationContext:
        """Build tool authorization context from trusted runtime session state."""
        return ToolAuthorizationContext(
            runtime_session_id=session.runtime_session_id,
            assistant_session_id=session.assistant_session_id,
            customer_id=session.customer_id,
            scope_mode=session.scope_mode,
            allowed_manufacturer_ids=session.allowed_manufacturer_ids,
            assistant_scopes=session.assistant_scopes,
        )

    def require_scope(
        self,
        context: ToolAuthorizationContext,
        required_scope: AssistantScope,
    ) -> None:
        """Require a backend-issued assistant scope before tool execution."""
        if required_scope.value not in set(context.assistant_scopes):
            raise MissingToolScopeError(
                details={
                    "required_scope": required_scope.value,
                    "runtime_session_id": context.runtime_session_id,
                }
            )

    def validate_manufacturer_access(
        self,
        context: ToolAuthorizationContext,
        requirement: ManufacturerScopeRequirement,
        requested_manufacturer_id: str | None = None,
    ) -> None:
        """Validate manufacturer access for scoped tool execution."""
        requested = self._normalize_optional_string(requested_manufacturer_id)
        allowed = {item for item in context.allowed_manufacturer_ids if item}

        if requirement == ManufacturerScopeRequirement.NONE and requested is None:
            return

        if requirement == ManufacturerScopeRequirement.REQUIRED and requested is None:
            raise InvalidManufacturerAccessError(
                "A manufacturer-scoped tool requires a manufacturer id."
            )

        if requested and allowed and requested not in allowed:
            raise InvalidManufacturerAccessError(
                details={
                    "requested_manufacturer_id": requested,
                    "allowed_manufacturer_ids": sorted(allowed),
                }
            )

    def require_permissions(
        self,
        principal: ValidatedAssistantClaims,
        required_permissions: list[str],
    ) -> None:
        """Compatibility helper for older route code."""
        missing = set(required_permissions) - set(principal.permissions)
        if missing:
            raise AuthorizationError(
                "The delegated principal lacks required tool permissions.",
                details={"missing_permissions": sorted(missing)},
            )

    @staticmethod
    def manufacturer_id_from_input(input_payload: dict[str, Any]) -> str | None:
        """Extract a manufacturer id from common tool input field names."""
        value = (
            input_payload.get("manufacturerId")
            or input_payload.get("manufacturer_id")
        )
        return AuthorizationService._normalize_optional_string(value)

    @staticmethod
    def _normalize_optional_string(value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None
