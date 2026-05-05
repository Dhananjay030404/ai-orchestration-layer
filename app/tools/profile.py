"""Customer profile assistant tool."""

import logging
from time import perf_counter
from typing import Any

from app.models.common import ApiModel
from app.models.tools import (
    AssistantScope,
    ManufacturerScopeRequirement,
    ToolAuthorizationContext,
    ToolExecutionResponse,
)
from app.models.session import RuntimeSession
from app.services.vam_client import VamClient
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ProfileReadInput(ApiModel):
    """No caller-supplied identifiers are accepted for profile reads."""


class ProfileReadTool(BaseTool):
    """Read the trusted customer's assistant-safe profile."""

    name = "profile_read"
    description = "Read the trusted customer's assistant-safe profile through VAM backend APIs."
    required_scope = AssistantScope.CUSTOMER_PROFILE_READ
    input_schema = {"type": "object", "properties": {}, "additionalProperties": False}
    input_model = ProfileReadInput
    authorization_rules = {"customerContext": "token"}
    manufacturer_scope = ManufacturerScopeRequirement.NONE

    def __init__(self, *, vam_client: VamClient | None = None) -> None:
        self._vam_client = vam_client or VamClient()

    async def execute(
        self,
        *,
        input_payload: dict[str, Any],
        auth_context: ToolAuthorizationContext,
        runtime_session: RuntimeSession,
    ) -> ToolExecutionResponse:
        """Fetch and normalize the customer profile for assistant consumption."""
        started_at = perf_counter()
        logger.info(
            "tool.profile_read.start",
            extra={
                "toolName": self.name,
                "runtimeSessionId": auth_context.runtime_session_id,
                "customerId": auth_context.customer_id,
            },
        )

        try:
            backend_payload = await self._vam_client.get_customer_profile(
                runtime_session,
                tool_name=self.name,
                correlation_id=auth_context.runtime_session_id,
            )
        except Exception:
            logger.exception(
                "tool.profile_read.failed",
                extra={
                    "toolName": self.name,
                    "runtimeSessionId": auth_context.runtime_session_id,
                    "customerId": auth_context.customer_id,
                    "durationMs": self._elapsed_ms(started_at),
                },
            )
            raise

        result = self._normalize_profile(backend_payload)
        metadata = {
            "source": "vam_backend",
            "runtimeSessionId": auth_context.runtime_session_id,
        }
        logger.info(
            "tool.profile_read.completed",
            extra={
                "toolName": self.name,
                "runtimeSessionId": auth_context.runtime_session_id,
                "customerId": auth_context.customer_id,
                "durationMs": self._elapsed_ms(started_at),
            },
        )
        return self.format_output(result, metadata=metadata)

    def _normalize_profile(self, payload: dict[str, Any]) -> dict[str, Any]:
        profile = self._profile_source(payload)
        first_name = self._first_present_string(
            profile,
            "firstName",
            "first_name",
            "givenName",
            "given_name",
        )
        last_name = self._first_present_string(
            profile,
            "lastName",
            "last_name",
            "familyName",
            "family_name",
        )

        normalized = {
            "profile": self._drop_none_values(
                {
                    "displayName": self._display_name(profile, first_name, last_name),
                    "firstName": first_name,
                    "lastName": last_name,
                    "email": self._first_present_string(
                        profile,
                        "email",
                        "emailAddress",
                        "email_address",
                    ),
                    "phone": self._first_present_string(
                        profile,
                        "phone",
                        "phoneNumber",
                        "phone_number",
                        "mobile",
                    ),
                    "locale": self._first_present_string(profile, "locale", "language"),
                    "timezone": self._first_present_string(
                        profile,
                        "timezone",
                        "timeZone",
                        "time_zone",
                    ),
                    "address": self._normalize_address(profile),
                }
            )
        }
        return normalized

    @staticmethod
    def _profile_source(payload: dict[str, Any]) -> dict[str, Any]:
        for key in ("profile", "customer", "data"):
            value = payload.get(key)
            if isinstance(value, dict):
                return value
        return payload

    def _display_name(
        self,
        profile: dict[str, Any],
        first_name: str | None,
        last_name: str | None,
    ) -> str | None:
        explicit_name = self._first_present_string(
            profile,
            "displayName",
            "display_name",
            "fullName",
            "full_name",
            "name",
        )
        if explicit_name:
            return explicit_name

        parts = [part for part in (first_name, last_name) if part]
        return " ".join(parts) or None

    def _normalize_address(self, profile: dict[str, Any]) -> dict[str, Any] | None:
        address = (
            profile.get("address")
            or profile.get("primaryAddress")
            or profile.get("primary_address")
        )
        if not isinstance(address, dict):
            return None

        normalized = self._drop_none_values(
            {
                "line1": self._first_present_string(
                    address,
                    "line1",
                    "addressLine1",
                    "address_line_1",
                ),
                "line2": self._first_present_string(
                    address,
                    "line2",
                    "addressLine2",
                    "address_line_2",
                ),
                "city": self._first_present_string(address, "city"),
                "state": self._first_present_string(address, "state", "region", "province"),
                "postalCode": self._first_present_string(
                    address,
                    "postalCode",
                    "postal_code",
                    "zip",
                ),
                "country": self._first_present_string(
                    address,
                    "country",
                    "countryCode",
                    "country_code",
                ),
            }
        )
        return normalized or None

    @staticmethod
    def _first_present_string(values: dict[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = values.get(key)
            if value is None:
                continue
            normalized = str(value).strip()
            if normalized:
                return normalized
        return None

    @staticmethod
    def _drop_none_values(values: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in values.items() if value is not None}

    @staticmethod
    def _elapsed_ms(started_at: float) -> float:
        return round((perf_counter() - started_at) * 1000, 2)
