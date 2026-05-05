"""Models for the ElevenLabs conversation runtime boundary."""

from typing import Literal

from pydantic import Field

from app.models.common import ApiModel


class ElevenLabsConversationSessionRequest(ApiModel):
    """Internal request to initialize an ElevenLabs conversation session."""

    runtime_session_id: str = Field(..., min_length=1)
    agent_id: str | None = None


class ElevenLabsConversationSession(ApiModel):
    """Provider session metadata returned by ElevenLabs."""

    provider: Literal["elevenlabs"] = "elevenlabs"
    agent_id: str
    conversation_id: str = Field(..., min_length=1)
    signed_url: str | None = None
