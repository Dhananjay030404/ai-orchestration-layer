from elevenlabs.types.conversation_initiation_client_data_internal import (
    ConversationInitiationClientDataInternal,
)
from elevenlabs.types.webhook_tool_api_schema_config_input import WebhookToolApiSchemaConfigInput


def test_elevenlabs_sdk_supports_dynamic_variables_and_server_tool_headers() -> None:
    """Guard the expected ElevenLabs server-tool auth wiring surface."""
    assert "dynamic_variables" in ConversationInitiationClientDataInternal.model_fields
    assert "request_headers" in WebhookToolApiSchemaConfigInput.model_fields
