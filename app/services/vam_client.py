"""Async client boundary for VAM internal backend APIs.

Assistant tools must call VAM business APIs through this Python service. This
client centralizes outbound HTTP behavior so tools do not know about base URLs,
timeouts, headers, logging, or backend error mapping.
"""

import logging
from time import perf_counter
from typing import Any, Mapping
from urllib.parse import quote

import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    BackendClientConfigurationError,
    BackendClientError,
    BackendClientHTTPError,
    BackendClientNetworkError,
    BackendClientResponseError,
    BackendClientTimeoutError,
)
from app.models.session import RuntimeSession

logger = logging.getLogger(__name__)

JsonObject = dict[str, Any]
QueryParams = Mapping[str, Any] | None
BackendSessionContext = RuntimeSession


class VamBackendClient:
    """HTTP client for Python-mediated VAM backend operations."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._client = http_client
        self._owns_client = http_client is None

    async def get_customer_profile(
        self,
        session: BackendSessionContext,
        *,
        tool_name: str,
        correlation_id: str | None = None,
    ) -> JsonObject:
        """Read the trusted customer's profile from the VAM backend."""
        path = self._format_path(
            self._require_path_template(
                self.settings.vam_backend_profile_path_template,
                "VAM_BACKEND_PROFILE_PATH_TEMPLATE",
            ),
            customer_id=session.customer_id,
            id=session.customer_id,
        )
        return await self.request(
            "GET",
            path,
            session=session,
            tool_name=tool_name,
            intent="customer_profile.read",
            correlation_id=correlation_id,
        )

    async def list_customer_assets(
        self,
        session: BackendSessionContext,
        *,
        tool_name: str,
        page: int | None = None,
        count: int | None = None,
        search: str | None = None,
        sort_field: str | None = None,
        order_by: str | None = None,
        equipment_id: str | None = None,
        manufacturer_id: str | None = None,
        non_onboarded_manufacturer_id: str | None = None,
        purchase_date: str | None = None,
        dealer_name: str | None = None,
        is_model_linked: bool | None = None,
        manufacturer_type: str | None = None,
        correlation_id: str | None = None,
    ) -> JsonObject:
        """List customer assets from the VAM backend."""
        path = self._format_path(
            self._require_path_template(
                self.settings.vam_backend_asset_list_path_template,
                "VAM_BACKEND_ASSET_LIST_PATH_TEMPLATE",
            ),
        )
        params = self._optional_params(
            page=page,
            count=count,
            search=search,
            sortField=sort_field,
            orderBy=order_by,
            equipmentId=equipment_id,
            manufacturerId=manufacturer_id,
            nonOnboardedManufacturerId=non_onboarded_manufacturer_id,
            purchaseDate=purchase_date,
            dealerName=dealer_name,
            isModelLinked=is_model_linked,
            manufacturerType=manufacturer_type,
        )
        return await self.request(
            "GET",
            path,
            session=session,
            tool_name=tool_name,
            intent="customer_asset.read",
            correlation_id=correlation_id,
            params=params,
        )

    async def request(
        self,
        method: str,
        path: str,
        *,
        session: BackendSessionContext,
        tool_name: str,
        intent: str,
        correlation_id: str | None = None,
        params: QueryParams = None,
        json_body: JsonObject | None = None,
    ) -> JsonObject:
        """Execute a VAM backend request with trusted session propagation."""
        method_upper = method.upper()
        headers = self._build_headers(
            session=session,
            tool_name=tool_name,
            correlation_id=correlation_id,
        )
        client = self._get_client()
        started_at = perf_counter()

        try:
            response = await client.request(
                method_upper,
                path,
                headers=headers,
                params=params,
                json=json_body,
            )
            duration_ms = self._elapsed_ms(started_at)
            self._log_response(
                "vam_backend.response",
                session=session,
                correlation_id=correlation_id,
                intent=intent,
                method=method_upper,
                path=path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
            response.raise_for_status()
            return self._decode_json_object(response, intent=intent)
        except httpx.TimeoutException as exc:
            duration_ms = self._elapsed_ms(started_at)
            self._log_failure(
                "vam_backend.timeout",
                session=session,
                correlation_id=correlation_id,
                intent=intent,
                method=method_upper,
                path=path,
                duration_ms=duration_ms,
            )
            raise BackendClientTimeoutError(
                details={
                    "intent": intent,
                    "method": method_upper,
                    "duration_ms": duration_ms,
                }
            ) from exc
        except httpx.HTTPStatusError as exc:
            response = exc.response
            self._log_failure(
                "vam_backend.http_error",
                session=session,
                correlation_id=correlation_id,
                intent=intent,
                method=method_upper,
                path=path,
                status_code=response.status_code,
            )
            raise BackendClientHTTPError(
                details={
                    "intent": intent,
                    "method": method_upper,
                    "status_code": response.status_code,
                }
            ) from exc
        except httpx.RequestError as exc:
            duration_ms = self._elapsed_ms(started_at)
            self._log_failure(
                "vam_backend.network_error",
                session=session,
                correlation_id=correlation_id,
                intent=intent,
                method=method_upper,
                path=path,
                duration_ms=duration_ms,
            )
            raise BackendClientNetworkError(
                details={
                    "intent": intent,
                    "method": method_upper,
                    "duration_ms": duration_ms,
                }
            ) from exc

    async def close(self) -> None:
        """Close the owned HTTP client, if one was created internally."""
        if self._client is not None and self._owns_client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "VamBackendClient":
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        await self.close()

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client

        if self.settings.vam_backend_base_url is None:
            raise BackendClientConfigurationError(
                "VAM_BACKEND_BASE_URL must be configured before assistant tools can call VAM APIs."
            )

        self._client = httpx.AsyncClient(
            base_url=str(self.settings.vam_backend_base_url).rstrip("/"),
            timeout=float(self.settings.vam_internal_api_timeout_seconds),
        )
        return self._client

    def _build_headers(
        self,
        *,
        session: BackendSessionContext,
        tool_name: str,
        correlation_id: str | None,
    ) -> dict[str, str]:
        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {session.delegated_assistant_token}",
            "x-runtime-session-id": session.runtime_session_id,
            "x-python-orchestrator": self.settings.app_name,
            "x-assistant-tool-name": tool_name,
        }

        if correlation_id:
            headers["x-correlation-id"] = correlation_id
        return headers

    def _decode_json_object(self, response: httpx.Response, *, intent: str) -> JsonObject:
        if response.status_code == 204 or not response.content:
            return {}

        try:
            payload = response.json()
        except ValueError as exc:
            raise BackendClientResponseError(
                "VAM backend returned invalid JSON.",
                details={"intent": intent, "status_code": response.status_code},
            ) from exc

        if isinstance(payload, dict):
            return payload

        return {"data": payload}

    def _log_response(
        self,
        message: str,
        *,
        session: BackendSessionContext,
        correlation_id: str | None,
        intent: str,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        logger.info(
            message,
            extra={
                "sessionId": session.runtime_session_id,
                "customerId": session.customer_id,
                "correlationId": correlation_id,
                "intent": intent,
                "method": method,
                "endpoint": intent,
                "statusCode": status_code,
                "durationMs": duration_ms,
            },
        )

    def _log_failure(
        self,
        message: str,
        *,
        session: BackendSessionContext,
        correlation_id: str | None,
        intent: str,
        method: str,
        path: str,
        status_code: int | None = None,
        duration_ms: float | None = None,
    ) -> None:
        logger.warning(
            message,
            extra={
                "sessionId": session.runtime_session_id,
                "customerId": session.customer_id,
                "correlationId": correlation_id,
                "intent": intent,
                "method": method,
                "endpoint": intent,
                "statusCode": status_code,
                "durationMs": duration_ms,
            },
        )

    @staticmethod
    def _require_path_template(value: str | None, setting_name: str) -> str:
        if value is None or not value.strip():
            raise BackendClientConfigurationError(
                f"{setting_name} must be configured before assistant tools can call VAM APIs.",
                details={"setting": setting_name},
            )

        normalized = value.strip()
        if not normalized.startswith("/"):
            raise BackendClientConfigurationError(
                f"{setting_name} must be a relative path that starts with '/'.",
                details={"setting": setting_name},
            )
        return normalized

    @staticmethod
    def _format_path(template: str, **values: str | int | None) -> str:
        encoded_values = {
            key: quote(VamBackendClient._require_identifier(value, key), safe="")
            for key, value in values.items()
        }
        try:
            return template.format(**encoded_values)
        except KeyError as exc:
            raise BackendClientConfigurationError(
                "Backend path template contains an unsupported placeholder.",
                details={
                    "placeholder": str(exc).strip("'"),
                    "supported_placeholders": sorted(encoded_values.keys()),
                },
            ) from exc

    @staticmethod
    def _require_identifier(value: str | int | None, field_name: str) -> str:
        if value is None:
            raise BackendClientError(
                "Backend request is missing a required identifier.",
                details={"field": field_name},
            )

        normalized = str(value).strip()
        if not normalized:
            raise BackendClientError(
                "Backend request is missing a required identifier.",
                details={"field": field_name},
            )
        return normalized

    @staticmethod
    def _optional_params(**values: Any) -> dict[str, Any]:
        return VamBackendClient._drop_none_values(dict(values))

    @staticmethod
    def _drop_none_values(values: JsonObject) -> JsonObject:
        return {key: value for key, value in values.items() if value is not None}

    @staticmethod
    def _elapsed_ms(started_at: float) -> float:
        return round((perf_counter() - started_at) * 1000, 2)


VamClient = VamBackendClient
