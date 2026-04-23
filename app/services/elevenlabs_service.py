"""ElevenLabs integration boundary for conversation and voice runtime."""

from app.core.config import Settings, get_settings
from app.models.elevenlabs import ElevenLabsRuntimeConfig, ElevenLabsWebhookEvent, WebhookAck
from app.models.session import SessionContext


class ElevenLabsService:
    """Prepare and handle ElevenLabs runtime data without delegating authority."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def prepare_runtime_session(self, session: SessionContext) -> ElevenLabsRuntimeConfig:
        """Return placeholder runtime config for a validated session.

        TODO: Create signed runtime setup with ElevenLabs once the provider contract is finalized.
        """
        if not self.settings.elevenlabs_agent_id:
            return ElevenLabsRuntimeConfig(status="not_configured")

        return ElevenLabsRuntimeConfig(
            status="prepared",
            agent_id=self.settings.elevenlabs_agent_id,
            conversation_id=session.elevenlabs_conversation_id,
        )

    async def handle_webhook(self, event: ElevenLabsWebhookEvent) -> WebhookAck:
        """Handle provider runtime events.

        TODO: Route events to the orchestration layer after signature validation is added.
        """
        return WebhookAck(accepted=True, event_id=event.event_id)
