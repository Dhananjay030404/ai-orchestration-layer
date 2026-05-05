"""ElevenLabs integration boundary for conversation and voice runtime."""

import inspect
import logging
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
from elevenlabs import AsyncElevenLabs

from app.core.config import Settings, get_settings
from app.core.exceptions import VendorIntegrationError
from app.models.elevenlabs import (
    ElevenLabsConversationSession,
    ElevenLabsConversationSessionRequest,
)


logger = logging.getLogger(__name__)


class ElevenLabsService:
    """Prepare and handle ElevenLabs runtime data without delegating authority."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def initialize_conversation_session(
        self,
        request: ElevenLabsConversationSessionRequest,
    ) -> ElevenLabsConversationSession:
        """Initialize an ElevenLabs conversation session for a trusted runtime session."""
        agent_id = request.agent_id or self.settings.elevenlabs_agent_id
        if not agent_id:
            raise VendorIntegrationError(
                "ElevenLabs agent id is required to initialize a conversation session."
            )

        if not self.settings.elevenlabs_api_key:
            raise VendorIntegrationError(
                "ElevenLabs API key is required to initialize a conversation session."
            )

        payload = await self._request_signed_url(agent_id)
        signed_url = self._optional_string(payload.get("signed_url"))
        conversation_id = self._conversation_id_from_payload(payload, signed_url)

        if not conversation_id:
            raise VendorIntegrationError("ElevenLabs did not return a conversation id.")

        return ElevenLabsConversationSession(
            agent_id=agent_id,
            conversation_id=conversation_id,
            signed_url=signed_url,
        )

    async def _request_signed_url(self, agent_id: str) -> dict[str, Any]:
        """Request a signed conversation URL from ElevenLabs using the official SDK."""
        httpx_client = httpx.AsyncClient(timeout=float(self.settings.elevenlabs_timeout_seconds))
        client = AsyncElevenLabs(
            api_key=self.settings.elevenlabs_api_key,
            base_url=str(self.settings.elevenlabs_base_url).rstrip("/"),
            timeout=float(self.settings.elevenlabs_timeout_seconds),
            httpx_client=httpx_client,
        )
        get_signed_url = client.conversational_ai.conversations.get_signed_url

        try:
            response = get_signed_url(
                agent_id=agent_id,
                include_conversation_id=True,
            )
            if inspect.isawaitable(response):
                response = await response
        except Exception as exc:
            logger.warning(
                "ElevenLabs signed URL request failed",
                extra={"error_type": type(exc).__name__},
            )
            raise VendorIntegrationError("ElevenLabs conversation initialization failed.") from exc
        finally:
            await httpx_client.aclose()

        data = self._sdk_response_to_payload(response)
        if not data:
            raise VendorIntegrationError("ElevenLabs returned an invalid response.")

        return data

    @staticmethod
    def _sdk_response_to_payload(response: Any) -> dict[str, Any]:
        """Normalize SDK response objects into a simple payload dictionary."""
        if isinstance(response, dict):
            return response

        if hasattr(response, "model_dump"):
            data = response.model_dump()
            return data if isinstance(data, dict) else {}

        if hasattr(response, "dict"):
            data = response.dict()
            return data if isinstance(data, dict) else {}

        payload = {
            "signed_url": getattr(response, "signed_url", None),
            "conversation_id": getattr(response, "conversation_id", None),
            "conversationId": getattr(response, "conversationId", None),
        }
        return {key: value for key, value in payload.items() if value is not None}

    @staticmethod
    def _conversation_id_from_payload(payload: dict[str, Any], signed_url: str | None) -> str | None:
        """Return the provider conversation id from response data or signed URL query params."""
        conversation_id = payload.get("conversation_id") or payload.get("conversationId")
        if isinstance(conversation_id, str) and conversation_id.strip():
            return conversation_id.strip()

        if not signed_url:
            return None

        query = parse_qs(urlparse(signed_url).query)
        query_value = query.get("conversation_id") or query.get("conversationId")
        if query_value and query_value[0].strip():
            return query_value[0].strip()

        return None

    @staticmethod
    def _optional_string(value: Any) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None
