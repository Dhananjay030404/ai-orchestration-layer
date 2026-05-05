from datetime import datetime, timedelta, timezone

from elevenlabs.types.conversation_initiation_client_data_internal import (
    ConversationInitiationClientDataInternal,
)
from elevenlabs.types.webhook_tool_api_schema_config_input import WebhookToolApiSchemaConfigInput
import pytest

from app.core.config import Settings
from app.models.elevenlabs import ElevenLabsConversationSession
from app.models.session import RuntimeSessionCreateRequest, SessionChannel, ValidatedAssistantClaims
from app.repositories.session_repository import InMemorySessionRepository
from app.services.elevenlabs_service import ElevenLabsService
from app.services.session_service import SessionService
from app.services.token_validation_service import TokenValidationService


def test_elevenlabs_sdk_supports_dynamic_variables_and_server_tool_headers() -> None:
    """Guard the expected ElevenLabs server-tool auth wiring surface."""
    assert "dynamic_variables" in ConversationInitiationClientDataInternal.model_fields
    assert "request_headers" in WebhookToolApiSchemaConfigInput.model_fields


def test_elevenlabs_service_reads_conversation_id_from_signed_url() -> None:
    signed_url = (
        "wss://api.elevenlabs.io/v1/convai/conversation?"
        "agent_id=agent_123&conversation_id=conv_123&conversation_signature=sig"
    )

    conversation_id = ElevenLabsService._conversation_id_from_payload({}, signed_url)

    assert conversation_id == "conv_123"


@pytest.mark.asyncio
async def test_session_bootstrap_attaches_elevenlabs_and_runtime_tool_token() -> None:
    settings = Settings(
        _env_file=None,
        assistant_jwt_secret="x" * 64,
        assistant_session_ttl_seconds=600,
    )
    session_service = SessionService(InMemorySessionRepository(), settings=settings)
    claims = _claims()

    bootstrap = await session_service.bootstrap_runtime_session(
        RuntimeSessionCreateRequest(
            claims=claims,
            delegated_assistant_token="delegated.jwt",
            channel=SessionChannel.ELEVENLABS,
            initialize_elevenlabs=True,
        ),
        elevenlabs_service=FakeElevenLabsService(),
    )

    token = TokenValidationService(settings=settings).mint_runtime_tool_token(
        bootstrap.runtime_session
    )
    runtime_claims = TokenValidationService(settings=settings).validate_runtime_tool_token_sync(token)

    assert bootstrap.elevenlabs_session is not None
    assert bootstrap.elevenlabs_session.conversation_id == "conv_test"
    assert bootstrap.runtime_session.elevenlabs_conversation_id == "conv_test"
    assert runtime_claims.runtime_session_id == bootstrap.runtime_session.runtime_session_id
    assert runtime_claims.assistant_session_id == claims.session_id
    assert runtime_claims.customer_id == claims.customer_id


class FakeElevenLabsService:
    async def initialize_conversation_session(self, request):
        return ElevenLabsConversationSession(
            agent_id=request.agent_id or "agent_test",
            conversation_id="conv_test",
            signed_url="wss://elevenlabs.test/conversation?conversation_id=conv_test",
        )


def _claims() -> ValidatedAssistantClaims:
    now = datetime.now(timezone.utc)
    return ValidatedAssistantClaims(
        session_id="assistant-session-1",
        customer_id="2903",
        scope_mode="ALL_MANUFACTURERS",
        allowed_manufacturer_ids=["6054"],
        assistant_scopes=["CUSTOMER_PROFILE_READ", "CUSTOMER_ASSET_READ"],
        issuer="aftermarket-backend",
        audience="vam-python-assistant",
        issued_at=now,
        expires_at=now + timedelta(minutes=5),
        token_id="token-1",
    )
