from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs

import httpx
import pytest

from app.core.config import Settings
from app.core.exceptions import BackendClientConfigurationError
from app.models.session import RuntimeSession
from app.services.vam_client import VamBackendClient


@pytest.mark.asyncio
async def test_profile_read_uses_configured_path_template_and_headers() -> None:
    seen: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["authorization"] = request.headers.get("authorization")
        seen["runtime_session_id"] = request.headers.get("x-runtime-session-id")
        seen["tool_name"] = request.headers.get("x-assistant-tool-name")
        return httpx.Response(
            200,
            json={"profile": {"firstName": "Casey", "email": "casey@example.com"}},
        )

    client = VamBackendClient(
        settings=_settings(
            vam_backend_profile_path_template="/private/customer/{id}",
        ),
        http_client=httpx.AsyncClient(
            base_url="https://vam-backend.test",
            transport=httpx.MockTransport(handler),
        ),
    )

    payload = await client.get_customer_profile(
        _runtime_session(customer_id="2903", delegated_token="delegated.jwt"),
        tool_name="profile_read",
        correlation_id="corr-1",
    )

    assert payload["profile"]["firstName"] == "Casey"
    assert seen == {
        "path": "/private/customer/2903",
        "authorization": "Bearer delegated.jwt",
        "runtime_session_id": "runtime-session-1",
        "tool_name": "profile_read",
    }


@pytest.mark.asyncio
async def test_asset_listing_uses_configured_path_template_and_query_params() -> None:
    seen: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["query"] = parse_qs(request.url.query.decode())
        return httpx.Response(
            200,
            json={"assets": [{"id": 115}], "recordsTotal": 1, "recordsFiltered": 1},
        )

    client = VamBackendClient(
        settings=_settings(vam_backend_asset_list_path_template="/private/assets"),
        http_client=httpx.AsyncClient(
            base_url="https://vam-backend.test",
            transport=httpx.MockTransport(handler),
        ),
    )

    payload = await client.list_customer_assets(
        _runtime_session(),
        tool_name="customer_asset",
        page=0,
        count=10,
        search="pump",
        manufacturer_id="6054",
    )

    assert payload["assets"] == [{"id": 115}]
    assert seen["path"] == "/private/assets"
    assert seen["query"] == {
        "page": ["0"],
        "count": ["10"],
        "search": ["pump"],
        "manufacturerId": ["6054"],
    }


@pytest.mark.asyncio
async def test_missing_backend_path_template_fails_with_configuration_error() -> None:
    client = VamBackendClient(
        settings=_settings(vam_backend_profile_path_template=None),
        http_client=httpx.AsyncClient(
            base_url="https://vam-backend.test",
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json={})),
        ),
    )

    with pytest.raises(BackendClientConfigurationError) as exc_info:
        await client.get_customer_profile(_runtime_session(), tool_name="profile_read")

    assert exc_info.value.code == "backend_client_configuration_error"
    assert exc_info.value.details == {"setting": "VAM_BACKEND_PROFILE_PATH_TEMPLATE"}


@pytest.mark.asyncio
async def test_unsupported_path_placeholder_fails_with_configuration_error() -> None:
    client = VamBackendClient(
        settings=_settings(
            vam_backend_profile_path_template="/private/customer/{customerUuid}",
        ),
        http_client=httpx.AsyncClient(
            base_url="https://vam-backend.test",
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json={})),
        ),
    )

    with pytest.raises(BackendClientConfigurationError) as exc_info:
        await client.get_customer_profile(_runtime_session(), tool_name="profile_read")

    assert exc_info.value.details["placeholder"] == "customerUuid"
    assert exc_info.value.details["supported_placeholders"] == ["customer_id", "id"]


def _settings(**overrides: object) -> Settings:
    values = {
        "assistant_jwt_secret": "x" * 64,
        "vam_backend_base_url": "https://vam-backend.test",
        "vam_backend_profile_path_template": "/private/customer/{customer_id}",
        "vam_backend_asset_list_path_template": "/private/assets",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def _runtime_session(
    *,
    customer_id: str = "2903",
    delegated_token: str = "delegated-token",
) -> RuntimeSession:
    now = datetime.now(timezone.utc)
    return RuntimeSession(
        runtime_session_id="runtime-session-1",
        assistant_session_id="assistant-session-1",
        customer_id=customer_id,
        delegated_assistant_token=delegated_token,
        scope_mode="ALL_MANUFACTURERS",
        allowed_manufacturer_ids=["6054"],
        assistant_scopes=["CUSTOMER_PROFILE_READ", "CUSTOMER_ASSET_READ"],
        expires_at=now + timedelta(minutes=5),
        created_at=now,
        updated_at=now,
    )
