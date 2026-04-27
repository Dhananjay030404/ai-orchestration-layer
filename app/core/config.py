"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import AliasChoices, AnyHttpUrl, Field, PositiveFloat, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the orchestration service."""

    app_name: str = Field(
        default="vam-ai-agent-service",
        validation_alias=AliasChoices("APP_NAME", "SERVICE_NAME"),
    )
    app_env: str = Field(default="local", validation_alias=AliasChoices("APP_ENV", "ENVIRONMENT"))
    app_host: str = "0.0.0.0"
    app_port: PositiveInt = 8000
    api_prefix: str = Field(default="/api/v1", validation_alias="API_PREFIX")
    log_level: str = "INFO"

    assistant_jwt_secret: str | None = None
    assistant_jwt_algorithm: str = "HS512"
    assistant_jwt_issuer: str | None = Field(
        default="aftermarket-backend",
        validation_alias=AliasChoices("ASSISTANT_JWT_ISSUER", "DELEGATED_TOKEN_ISSUER"),
    )
    assistant_jwt_audience: str = Field(
        default="vam-python-assistant",
        validation_alias=AliasChoices("ASSISTANT_JWT_AUDIENCE", "DELEGATED_TOKEN_AUDIENCE"),
    )
    assistant_session_ttl_seconds: PositiveInt = Field(
        default=3600,
        validation_alias=AliasChoices("ASSISTANT_SESSION_TTL_SECONDS", "SESSION_TTL_SECONDS"),
    )

    elevenlabs_api_key: str | None = None
    elevenlabs_agent_id: str | None = None
    elevenlabs_base_url: AnyHttpUrl = "https://api.elevenlabs.io"
    elevenlabs_timeout_seconds: PositiveFloat = 10.0

    vam_backend_base_url: AnyHttpUrl | None = None
    vam_internal_api_timeout_seconds: PositiveFloat = Field(
        default=10.0,
        validation_alias=AliasChoices(
            "VAM_INTERNAL_API_TIMEOUT_SECONDS",
            "VAM_BACKEND_TIMEOUT_SECONDS",
        ),
    )

    redis_url: str | None = None

    delegated_token_public_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DELEGATED_TOKEN_PUBLIC_KEY", "ASSISTANT_JWT_SECRET"),
    )
    delegated_token_jwks_url: AnyHttpUrl | None = None
    delegated_token_algorithms: list[str] = Field(default_factory=lambda: ["HS512"])

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        validate_default=True,
    )

    @property
    def service_name(self) -> str:
        """Backward-compatible service name used by earlier modules."""
        return self.app_name

    @property
    def environment(self) -> str:
        """Backward-compatible environment name used by earlier modules."""
        return self.app_env

    @property
    def session_ttl_seconds(self) -> int:
        """Backward-compatible session TTL used by the session service."""
        return self.assistant_session_ttl_seconds

    @property
    def vam_backend_timeout_seconds(self) -> float:
        """Backward-compatible backend timeout setting."""
        return self.vam_internal_api_timeout_seconds

    @property
    def delegated_token_issuer(self) -> str | None:
        """Backward-compatible JWT issuer setting."""
        return self.assistant_jwt_issuer

    @property
    def delegated_token_audience(self) -> str:
        """Backward-compatible JWT audience setting."""
        return self.assistant_jwt_audience


@lru_cache
def get_settings() -> Settings:
    """Return cached settings for dependency injection."""
    return Settings()
