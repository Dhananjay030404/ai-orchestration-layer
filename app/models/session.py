"""Session request and response models."""

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import Field, field_validator

from app.models.common import ApiModel


def normalize_string_list(value: Any) -> list[str]:
    """Accept common list encodings and normalize members to non-empty strings."""
    if value is None:
        return []
    if isinstance(value, str):
        items = value.split(" ")
    elif isinstance(value, list):
        items = value
    else:
        raise ValueError("Claim must be a string or list of strings.")

    return [str(item).strip() for item in items if str(item).strip()]


class ValidatedAssistantClaims(ApiModel):
    """Normalized trusted claims from a delegated assistant JWT."""

    session_id: str = Field(..., min_length=1)
    customer_id: str = Field(..., min_length=1)
    scope_mode: str = Field(..., min_length=1)
    allowed_manufacturer_ids: list[str] = Field(default_factory=list)
    assistant_scopes: list[str] = Field(default_factory=list)
    issuer: str = Field(..., min_length=1)
    audience: str = Field(..., min_length=1)
    issued_at: datetime
    expires_at: datetime
    token_id: str | None = None

    @field_validator("allowed_manufacturer_ids", "assistant_scopes", mode="before")
    @classmethod
    def normalize_string_list(cls, value: Any) -> list[str]:
        """Accept common JWT list encodings and normalize members to strings."""
        return normalize_string_list(value)

    @field_validator("assistant_scopes")
    @classmethod
    def require_assistant_scopes(cls, value: list[str]) -> list[str]:
        """Require at least one backend-issued assistant scope."""
        if not value:
            raise ValueError("assistant_scopes must not be empty.")
        return value

    @property
    def subject(self) -> str:
        """Compatibility identity field for existing authorization code."""
        return self.customer_id

    @property
    def permissions(self) -> list[str]:
        """Compatibility permissions field for existing tool authorization."""
        return self.assistant_scopes

    @property
    def scopes(self) -> list[str]:
        """Compatibility scopes field for existing callers."""
        return self.assistant_scopes


class RuntimeToolClaims(ApiModel):
    """Trusted claims from a Python-issued runtime tool token."""

    token_id: str = Field(..., min_length=1)
    token_use: Literal["runtime_tool"] = Field(..., alias="tokenUse")
    runtime_session_id: str = Field(..., min_length=1, alias="runtimeSessionId")
    assistant_session_id: str = Field(..., min_length=1, alias="assistantSessionId")
    customer_id: str = Field(..., min_length=1, alias="customerId")
    issuer: str = Field(..., min_length=1)
    audience: str = Field(..., min_length=1)
    issued_at: datetime
    expires_at: datetime


class RuntimeSessionStatus(str, Enum):
    """Lifecycle states for a Python runtime session."""

    CREATED = "created"
    ACTIVE = "active"
    EXPIRED = "expired"
    CLOSED = "closed"


class SessionChannel(str, Enum):
    """Runtime channel that initiated the session."""

    ELEVENLABS = "elevenlabs"


class UserContext(ApiModel):
    """Trusted identity and scope state used by secure runtime services."""

    customer_id: str = Field(..., min_length=1)
    scope_mode: str = Field(..., min_length=1)
    allowed_manufacturer_ids: list[str] = Field(default_factory=list)
    assistant_scopes: list[str] = Field(default_factory=list)

    @field_validator("allowed_manufacturer_ids", "assistant_scopes", mode="before")
    @classmethod
    def normalize_string_list(cls, value: Any) -> list[str]:
        """Accept common list encodings and normalize members to strings."""
        return normalize_string_list(value)

    @field_validator("assistant_scopes")
    @classmethod
    def require_assistant_scopes(cls, value: list[str]) -> list[str]:
        """Require at least one backend-issued assistant scope."""
        if not value:
            raise ValueError("assistant_scopes must not be empty.")
        return value

    @property
    def subject(self) -> str:
        """Compatibility identity field for existing authorization code."""
        return self.customer_id

    @property
    def permissions(self) -> list[str]:
        """Compatibility permissions field for existing tool authorization."""
        return self.assistant_scopes

    @property
    def scopes(self) -> list[str]:
        """Compatibility scopes field for existing callers."""
        return self.assistant_scopes


class RuntimeSessionCreateRequest(ApiModel):
    """Internal request to create a runtime session from validated claims."""

    claims: ValidatedAssistantClaims
    delegated_assistant_token: str = Field(..., min_length=1)
    channel: SessionChannel = SessionChannel.ELEVENLABS
    agent_id: str | None = None
    initialize_elevenlabs: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeSessionBootstrapRequest(ApiModel):
    """Optional ElevenLabs runtime bootstrap inputs that do not affect trusted identity."""

    agent_id: str | None = Field(default=None, alias="agentId")


class RuntimeSessionCreateResponse(ApiModel):
    """Response returned after a runtime session is created."""

    runtime_session_id: str = Field(..., alias="runtimeSessionId")
    assistant_session_id: str = Field(..., alias="assistantSessionId")
    status: RuntimeSessionStatus
    expires_at: datetime = Field(..., alias="expiresAt")
    channel: SessionChannel
    agent_id: str | None = Field(default=None, alias="agentId")
    elevenlabs_conversation_id: str | None = Field(default=None, alias="elevenlabsConversationId")
    elevenlabs_signed_url: str | None = Field(default=None, alias="elevenlabsSignedUrl")
    runtime_tool_token: str | None = Field(default=None, alias="runtimeToolToken")
    elevenlabs_dynamic_variables: dict[str, str] = Field(
        default_factory=dict,
        alias="elevenlabsDynamicVariables",
    )


class RuntimeSession(ApiModel):
    """Authoritative Python runtime session state."""

    runtime_session_id: str = Field(..., min_length=1)
    assistant_session_id: str = Field(..., min_length=1)
    customer_id: str = Field(..., min_length=1)
    delegated_assistant_token: str = Field(..., min_length=1)
    scope_mode: str = Field(..., min_length=1)
    allowed_manufacturer_ids: list[str] = Field(default_factory=list)
    assistant_scopes: list[str] = Field(default_factory=list)
    expires_at: datetime
    created_at: datetime
    updated_at: datetime
    status: RuntimeSessionStatus = RuntimeSessionStatus.CREATED
    channel: SessionChannel = SessionChannel.ELEVENLABS
    agent_id: str | None = None
    elevenlabs_conversation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("allowed_manufacturer_ids", "assistant_scopes", mode="before")
    @classmethod
    def normalize_string_list(cls, value: Any) -> list[str]:
        """Accept common list encodings and normalize members to strings."""
        return normalize_string_list(value)

    @field_validator("assistant_scopes")
    @classmethod
    def require_assistant_scopes(cls, value: list[str]) -> list[str]:
        """Require at least one backend-issued assistant scope."""
        if not value:
            raise ValueError("assistant_scopes must not be empty.")
        return value

    @property
    def session_id(self) -> str:
        """Compatibility identifier used by existing routes."""
        return self.runtime_session_id

    @property
    def user_context(self) -> UserContext:
        """Return the trusted runtime user context."""
        return UserContext(
            customer_id=self.customer_id,
            scope_mode=self.scope_mode,
            allowed_manufacturer_ids=self.allowed_manufacturer_ids,
            assistant_scopes=self.assistant_scopes,
        )

    @property
    def principal(self) -> UserContext:
        """Compatibility principal used by existing service/tool code."""
        return self.user_context


SessionContext = RuntimeSession
