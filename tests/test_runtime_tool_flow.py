from datetime import datetime, timedelta, timezone
import base64

import jwt
import pytest

from app.core.config import Settings
from app.core.exceptions import AuthorizationError
from app.models.session import RuntimeSessionCreateRequest, SessionChannel
from app.models.tools import ToolExecutionRequest
from app.repositories.session_repository import InMemorySessionRepository
from app.services.authorization_service import AuthorizationService
from app.services.session_service import SessionService
from app.services.token_validation_service import TokenValidationService
from app.services.tool_execution_service import ToolExecutionService
from app.tools.assets import CustomerAssetTool
from app.tools.profile import ProfileReadTool
from app.tools.registry import ToolRegistry


JWT_SECRET = "x" * 64


def test_delegated_jwt_validation_accepts_backend_session_response_claims() -> None:
    settings = _settings()
    now = datetime.now(timezone.utc)
    payload = {
        "iss": settings.assistant_jwt_issuer,
        "aud": settings.assistant_jwt_audience,
        "sub": "123",
        "customerId": 123,
        "jti": "assistant-session-1",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
        "scopeMode": "ALL_MANUFACTURERS",
        "allowedManufacturerIds": [10, 20, 30],
        "assistantScopes": ["CUSTOMER_PROFILE_READ"],
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=settings.assistant_jwt_algorithm)

    claims = TokenValidationService(settings=settings).validate_assistant_token_sync(token)

    assert claims.customer_id == "123"
    assert claims.session_id == "assistant-session-1"
    assert claims.scope_mode == "ALL_MANUFACTURERS"
    assert claims.allowed_manufacturer_ids == ["10", "20", "30"]
    assert claims.assistant_scopes == ["CUSTOMER_PROFILE_READ"]


def test_delegated_jwt_validation_accepts_base64_decoded_backend_secret() -> None:
    encoded_secret = "4f38e5a8538a50a5c9f8ba9e84234cf38084ed3fd4a5fd557fa23f8c89a294d968ae26f2b5e8f230a1f3314b24dbc891f6cc781f83b81220abd65a41608d9768"
    settings = _settings(assistant_jwt_secret=encoded_secret)
    now = datetime.now(timezone.utc)
    payload = {
        "iss": settings.assistant_jwt_issuer,
        "aud": settings.assistant_jwt_audience,
        "sub": "2903",
        "customerId": 2903,
        "jti": "assistant-session-1",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
        "scopeMode": "ALL_MANUFACTURERS",
        "assistantScopes": ["CUSTOMER_PROFILE_READ"],
    }
    token = jwt.encode(
        payload,
        base64.b64decode(encoded_secret + "==="),
        algorithm=settings.assistant_jwt_algorithm,
    )

    claims = TokenValidationService(settings=settings).validate_assistant_token_sync(token)

    assert claims.customer_id == "2903"


@pytest.mark.asyncio
async def test_runtime_tool_token_executes_profile_read_without_delegated_jwt() -> None:
    settings = _settings()
    now = datetime.now(timezone.utc)
    delegated_token = jwt.encode(
        {
            "iss": settings.assistant_jwt_issuer,
            "aud": settings.assistant_jwt_audience,
            "sub": "customer-1",
            "customerId": "customer-1",
            "jti": "assistant-session-1",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
            "scopeMode": "customer",
            "assistantScopes": ["CUSTOMER_PROFILE_READ", "CUSTOMER_ASSET_READ"],
        },
        JWT_SECRET,
        algorithm=settings.assistant_jwt_algorithm,
    )
    token_service = TokenValidationService(settings=settings)
    principal = await token_service.validate_delegated_token(delegated_token)

    session_service = SessionService(InMemorySessionRepository(), settings=settings)
    session = await session_service.create_runtime_session(
        RuntimeSessionCreateRequest(
            claims=principal,
            delegated_assistant_token=delegated_token,
            channel=SessionChannel.ELEVENLABS,
        )
    )
    runtime_tool_token = token_service.mint_runtime_tool_token(session)
    runtime_claims = await token_service.validate_runtime_tool_token(runtime_tool_token)

    execution_service = ToolExecutionService(
        session_service=session_service,
        authorization_service=AuthorizationService(),
        registry=ToolRegistry(
            [
                ProfileReadTool(vam_client=FakeVamClient()),
                CustomerAssetTool(vam_client=FakeVamClient()),
            ]
        ),
    )

    response = await execution_service.execute_for_runtime_tool_token(
        ToolExecutionRequest(
            runtimeSessionId=session.runtime_session_id,
            toolName="profile_read",
            parameters={},
        ),
        runtime_claims,
    )

    assert response.status.value == "completed"
    assert response.result == {
        "profile": {
            "displayName": "Runtime Token",
            "firstName": "Runtime",
            "lastName": "Token",
            "email": "runtime@example.com",
        }
    }
    assert "internalOnly" not in str(response.result)

    asset_response = await execution_service.execute_for_runtime_tool_token(
        ToolExecutionRequest(
            runtimeSessionId=session.runtime_session_id,
            toolName="customer_asset",
            parameters={"page": 0, "count": 10, "manufacturerId": "6054"},
        ),
        runtime_claims,
    )

    assert asset_response.status.value == "completed"
    assert asset_response.result == {
        "assets": [{"id": 115, "name": "Asset 115"}],
        "recordsTotal": 1,
        "recordsFiltered": 1,
        "totalPages": 1,
        "number": 0,
    }

    mismatched_request = ToolExecutionRequest(
        runtimeSessionId="another-runtime-session",
        toolName="profile_read",
        parameters={},
    )
    with pytest.raises(AuthorizationError):
        await execution_service.execute_for_runtime_tool_token(mismatched_request, runtime_claims)


class FakeVamClient:
    async def get_customer_profile(self, session, *, tool_name=None, correlation_id=None):
        return {
            "profile": {
                "firstName": "Runtime",
                "lastName": "Token",
                "email": "runtime@example.com",
                "internalOnly": "hidden",
            }
        }

    async def list_customer_assets(self, session, *, tool_name=None, correlation_id=None, **params):
        assert params["page"] == 0
        assert params["count"] == 10
        assert params["manufacturer_id"] == "6054"
        return {
            "assets": [{"id": 115, "name": "Asset 115"}],
            "recordsTotal": 1,
            "recordsFiltered": 1,
            "totalPages": 1,
            "number": 0,
        }


def _settings(**overrides) -> Settings:
    values = {
        "assistant_jwt_secret": JWT_SECRET,
        "assistant_jwt_algorithm": "HS512",
        "assistant_jwt_issuer": "aftermarket-backend",
        "assistant_jwt_audience": "vam-python-assistant",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)
