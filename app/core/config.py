"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import AliasChoices, AnyHttpUrl, Field, PositiveFloat, PositiveInt, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the assistant service."""

    app_name: str = Field(
        default="vam-ai-agent-service",
        validation_alias=AliasChoices("APP_NAME", "SERVICE_NAME"),
    )
    app_env: str = Field(default="local", validation_alias=AliasChoices("APP_ENV", "ENVIRONMENT"))
    app_host: str = "0.0.0.0"
    app_port: PositiveInt = 8000
    api_prefix: str = Field(default="/api/v1", validation_alias="API_PREFIX")
    log_level: str = "INFO"
    cors_allowed_origins_raw: str | None = Field(
        default=None,
        validation_alias=AliasChoices("CORS_ALLOWED_ORIGINS", "FRONTEND_ORIGINS"),
    )

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
        default=600,
        validation_alias=AliasChoices("ASSISTANT_SESSION_TTL_SECONDS", "SESSION_TTL_SECONDS"),
    )

    elevenlabs_api_key: str | None = None
    elevenlabs_agent_id: str | None = None
    elevenlabs_base_url: AnyHttpUrl = "https://api.elevenlabs.io"
    elevenlabs_timeout_seconds: PositiveFloat = 10.0

    vam_backend_base_url: AnyHttpUrl | None = None
    vam_backend_profile_path_template: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "VAM_BACKEND_PROFILE_PATH_TEMPLATE",
            "vam_backend_profile_path_template",
        ),
    )
    vam_backend_asset_list_path_template: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "VAM_BACKEND_ASSET_LIST_PATH_TEMPLATE",
            "vam_backend_asset_list_path_template",
        ),
    )
    vam_internal_api_timeout_seconds: PositiveFloat = Field(
        default=10.0,
        validation_alias=AliasChoices(
            "VAM_INTERNAL_API_TIMEOUT_SECONDS",
            "VAM_BACKEND_TIMEOUT_SECONDS",
        ),
    )

    session_repository_backend: str = Field(default="mysql", validation_alias="SESSION_REPOSITORY_BACKEND")
    mysql_host: str | None = Field(default=None, validation_alias="MYSQL_HOST")
    mysql_port: PositiveInt = Field(default=3306, validation_alias="MYSQL_PORT")
    mysql_database: str | None = Field(default=None, validation_alias="MYSQL_DATABASE")
    mysql_user: str | None = Field(default=None, validation_alias="MYSQL_USER")
    mysql_password: str | None = Field(default=None, validation_alias="MYSQL_PASSWORD")
    mysql_pool_min_size: PositiveInt = Field(default=1, validation_alias="MYSQL_POOL_MIN_SIZE")
    mysql_pool_max_size: PositiveInt = Field(default=10, validation_alias="MYSQL_POOL_MAX_SIZE")
    mysql_connect_timeout_seconds: PositiveFloat = Field(
        default=10.0,
        validation_alias="MYSQL_CONNECT_TIMEOUT_SECONDS",
    )

    delegated_token_public_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DELEGATED_TOKEN_PUBLIC_KEY", "ASSISTANT_JWT_SECRET"),
    )
    delegated_token_jwks_url: AnyHttpUrl | None = None
    delegated_token_algorithms: list[str] = Field(default_factory=lambda: ["HS512"])

    @field_validator(
        "assistant_jwt_secret",
        "elevenlabs_api_key",
        "elevenlabs_agent_id",
        "vam_backend_base_url",
        "vam_backend_profile_path_template",
        "vam_backend_asset_list_path_template",
        "cors_allowed_origins_raw",
        "mysql_host",
        "mysql_database",
        "mysql_user",
        "mysql_password",
        "delegated_token_public_key",
        "delegated_token_jwks_url",
        mode="before",
    )
    @classmethod
    def empty_string_as_none(cls, value: object) -> object:
        """Treat blank optional environment values as unset."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def validate_mysql_pool_sizes(self) -> "Settings":
        """Require a valid MySQL pool size range."""
        if self.mysql_pool_min_size > self.mysql_pool_max_size:
            raise ValueError("MYSQL_POOL_MIN_SIZE must not exceed MYSQL_POOL_MAX_SIZE.")
        return self

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
    def cors_allowed_origins(self) -> list[str]:
        """Return configured browser origins allowed to call this service."""
        if not self.cors_allowed_origins_raw:
            return []
        return [
            origin.strip()
            for origin in self.cors_allowed_origins_raw.split(",")
            if origin.strip()
        ]

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
