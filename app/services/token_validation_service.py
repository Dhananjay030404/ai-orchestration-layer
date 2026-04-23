"""Delegated assistant token validation service."""

from datetime import datetime, timezone
from typing import Any

import jwt
from jwt import InvalidTokenError

from app.core.config import Settings, get_settings
from app.core.exceptions import TokenValidationError
from app.models.common import DelegatedPrincipal


class TokenValidationService:
    """Validate delegated assistant tokens issued by the Spring Boot backend."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def validate_delegated_token(self, token: str) -> DelegatedPrincipal:
        """Validate a token and return trusted principal claims.

        TODO: Add JWKS fetching and cache rotation using delegated_token_jwks_url.
        """
        if not self.settings.delegated_token_public_key:
            raise TokenValidationError("Delegated token validation is not configured.")

        try:
            claims = jwt.decode(
                token,
                self.settings.delegated_token_public_key,
                algorithms=self.settings.delegated_token_algorithms,
                audience=self.settings.delegated_token_audience,
                issuer=self.settings.delegated_token_issuer,
            )
        except InvalidTokenError as exc:
            raise TokenValidationError() from exc

        return self._principal_from_claims(claims)

    def _principal_from_claims(self, claims: dict[str, Any]) -> DelegatedPrincipal:
        subject = claims.get("sub")
        customer_id = claims.get("customer_id")
        if not subject or not customer_id:
            raise TokenValidationError("Delegated token is missing required identity claims.")

        expires_at = self._datetime_from_epoch(claims.get("exp"))
        scopes = self._claim_list(claims.get("scope") or claims.get("scopes"))
        permissions = self._claim_list(claims.get("permissions"))

        return DelegatedPrincipal(
            subject=subject,
            customer_id=customer_id,
            manufacturer_id=claims.get("manufacturer_id"),
            scopes=scopes,
            permissions=permissions,
            expires_at=expires_at,
            token_id=claims.get("jti"),
            raw_claims=claims,
        )

    @staticmethod
    def _datetime_from_epoch(value: Any) -> datetime | None:
        if value is None:
            return None
        return datetime.fromtimestamp(int(value), tz=timezone.utc)

    @staticmethod
    def _claim_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [item for item in value.split(" ") if item]
        if isinstance(value, list):
            return [str(item) for item in value]
        return []
