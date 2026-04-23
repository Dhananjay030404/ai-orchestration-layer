"""Session request and response models."""

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from app.models.common import ApiModel, DelegatedPrincipal


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


class SessionContext(ApiModel):
    """Internal session state persisted by the repository."""

    session_id: str
    principal: DelegatedPrincipal
    created_at: datetime
    expires_at: datetime
    status: str = "created"
    elevenlabs_conversation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
