"""Webhook routes for inbound ElevenLabs runtime events."""

from fastapi import APIRouter

from app.models.elevenlabs import ElevenLabsWebhookEvent, WebhookAck
from app.services.audit_service import AuditService
from app.services.elevenlabs_service import ElevenLabsService


router = APIRouter(prefix="/webhooks/elevenlabs", tags=["webhooks"])


@router.post("", response_model=WebhookAck)
async def receive_elevenlabs_webhook(event: ElevenLabsWebhookEvent) -> WebhookAck:
    """Accept ElevenLabs runtime events for orchestration processing.

    TODO: Add provider signature validation before enabling this route in production.
    """
    await AuditService().record_event("elevenlabs.webhook.received", event.model_dump())
    return await ElevenLabsService().handle_webhook(event)
