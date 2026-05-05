from datetime import datetime, timedelta, timezone
import os

import pytest

from app.core.config import Settings
from app.models.session import RuntimeSession
from app.services.vam_client import VamBackendClient


@pytest.mark.asyncio
async def test_real_vam_customer_profile_endpoint_when_configured() -> None:
    """Optional live smoke for the VAM internal profile endpoint.

    Set VAM_PROFILE_INTEGRATION_CUSTOMER_ID, VAM_PROFILE_INTEGRATION_TOKEN,
    VAM_BACKEND_BASE_URL, and VAM_BACKEND_PROFILE_PATH_TEMPLATE to run it.
    """
    customer_id = os.getenv("VAM_PROFILE_INTEGRATION_CUSTOMER_ID")
    if not customer_id:
        pytest.skip("VAM_PROFILE_INTEGRATION_CUSTOMER_ID is not configured.")
    delegated_token = os.getenv("VAM_PROFILE_INTEGRATION_TOKEN")
    if not delegated_token:
        pytest.skip("VAM_PROFILE_INTEGRATION_TOKEN is not configured.")

    settings = Settings()
    if not settings.vam_backend_base_url:
        pytest.skip("VAM_BACKEND_BASE_URL is not configured.")
    if not settings.vam_backend_profile_path_template:
        pytest.skip("VAM_BACKEND_PROFILE_PATH_TEMPLATE is not configured.")

    now = datetime.now(timezone.utc)
    session = RuntimeSession(
        runtime_session_id="integration-runtime-session",
        assistant_session_id="integration-assistant-session",
        customer_id=customer_id,
        delegated_assistant_token=delegated_token,
        scope_mode="customer",
        assistant_scopes=["CUSTOMER_PROFILE_READ"],
        expires_at=now + timedelta(minutes=5),
        created_at=now,
        updated_at=now,
    )

    async with VamBackendClient(settings=settings) as client:
        payload = await client.get_customer_profile(
            session,
            tool_name="profile_read",
            correlation_id="integration-profile-read",
        )

    assert isinstance(payload, dict)
