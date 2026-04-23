"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the orchestration service."""

    service_name: str = "vam-ai-agent-service"
    environment: str = "local"
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"

    delegated_token_issuer: str = "vam-backend"
    delegated_token_audience: str = "vam-ai-agent-service"
    delegated_token_jwks_url: AnyHttpUrl | None = None
    delegated_token_public_key: str | None = None
    delegated_token_algorithms: list[str] = Field(default_factory=lambda: ["RS256"])

    vam_backend_base_url: AnyHttpUrl | None = None
    vam_backend_timeout_seconds: float = 10.0

    elevenlabs_api_key: str | None = None
    elevenlabs_agent_id: str | None = None

    session_ttl_seconds: int = 3600

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings for dependency injection."""
    return Settings()
