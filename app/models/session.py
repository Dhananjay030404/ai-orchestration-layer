"""Session request and response models."""

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_validator

from app.models.common import ApiModel


class SessionCreateRequest(ApiModel):
    """Request to create a Python orchestration session."""

    delegated_assistant_token: str = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionCreateResponse(ApiModel):
    """Response returned after a session is created."""

    session_id: str
    status: Literal["created"]
    expires_at: datetime
    elevenlabs_conversation_id: str | None = None


class SessionStatusResponse(ApiModel):
    """External session status response."""

    session_id: str
    status: str
    created_at: datetime
    expires_at: datetime
    elevenlabs_conversation_id: str | None = None


class ValidatedAssistantClaims(ApiModel):
    """Normalized trusted claims from a delegated assistant JWT."""

    session_id: str = Field(..., min_length=1)
    customer_id: str = Field(..., min_length=1)
    scope_mode: str = Field(..., min_length=1)
    active_manufacturer_id: str | None = None
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
        if value is None:
            return []
        if isinstance(value, str):
            items = value.split(" ")
        elif isinstance(value, list):
            items = value
        else:
            raise ValueError("Claim must be a string or list of strings.")

        normalized = [str(item).strip() for item in items if str(item).strip()]
        return normalized

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
        return self.session_id

    @property
    def manufacturer_id(self) -> str | None:
        """Compatibility manufacturer field for existing session checks."""
        return self.active_manufacturer_id

    @property
    def permissions(self) -> list[str]:
        """Compatibility permissions field for existing tool authorization."""
        return self.assistant_scopes

    @property
    def scopes(self) -> list[str]:
        """Compatibility scopes field for existing callers."""
        return self.assistant_scopes


class SessionContext(ApiModel):
    """Internal session state persisted by the repository."""

    session_id: str
    principal: ValidatedAssistantClaims
    created_at: datetime
    expires_at: datetime
    status: str = "created"
    elevenlabs_conversation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
