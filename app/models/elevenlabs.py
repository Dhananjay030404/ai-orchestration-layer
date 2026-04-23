"""Models for the ElevenLabs conversation runtime boundary."""

from typing import Any, Literal

from pydantic import Field

from app.models.common import ApiModel


class ElevenLabsRuntimeConfig(ApiModel):
    """Runtime data that can be passed to the voice/conversation layer."""

    provider: Literal["elevenlabs"] = "elevenlabs"
    status: Literal["prepared", "not_configured"] = "not_configured"
    agent_id: str | None = None
    conversation_id: str | None = None
    signed_url: str | None = None


class ElevenLabsWebhookEvent(ApiModel):
    """Inbound event envelope from ElevenLabs.

    TODO: Replace this generic payload with typed event variants when the webhook
    contract is finalized.
    """

    event_type: str = Field(..., min_length=1)
    event_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class WebhookAck(ApiModel):
    """Acknowledgement returned after accepting a webhook event."""

    accepted: bool
    event_id: str | None = None
