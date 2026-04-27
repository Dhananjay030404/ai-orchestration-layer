"""Delegated assistant token validation service."""

from datetime import datetime, timezone
from typing import Any

import jwt
from jwt import ExpiredSignatureError, InvalidAudienceError, InvalidIssuerError
from jwt import InvalidTokenError as PyJwtInvalidTokenError
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationError, ExpiredTokenError, InvalidTokenError
from app.models.session import ValidatedAssistantClaims


class TokenValidationService:
    """Validate delegated assistant tokens issued by the Spring Boot backend."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def validate_assistant_token(self, token: str) -> ValidatedAssistantClaims:
        """Validate a delegated assistant token and return normalized claims."""
        return self.validate_assistant_token_sync(token)

    async def validate_delegated_token(self, token: str) -> ValidatedAssistantClaims:
        """Backward-compatible name for existing route dependencies."""
        return await self.validate_assistant_token(token)

    def validate_assistant_token_sync(self, token: str) -> ValidatedAssistantClaims:
        """Synchronously validate a JWT for unit tests and non-async callers."""
        if not token or not token.strip():
            raise AuthenticationError("A delegated assistant token is required.")

        secret = self.settings.assistant_jwt_secret
        if not secret:
            raise AuthenticationError("Delegated assistant token validation is not configured.")

        issuer = self.settings.assistant_jwt_issuer
        if not issuer:
            raise AuthenticationError("Delegated assistant token issuer is not configured.")

        expected_algorithm = self.settings.assistant_jwt_algorithm
        self._validate_header_algorithm(token, expected_algorithm)

        try:
            raw_claims = jwt.decode(
                token,
                secret,
                algorithms=[expected_algorithm],
                audience=self.settings.assistant_jwt_audience,
                issuer=issuer,
                options={"require": ["exp", "iat", "iss", "aud", "sub", "jti"]},
            )
        except ExpiredSignatureError as exc:
            raise ExpiredTokenError() from exc
        except (InvalidAudienceError, InvalidIssuerError, PyJwtInvalidTokenError) as exc:
            raise InvalidTokenError() from exc

        return self._normalize_claims(raw_claims)

    @staticmethod
    def _validate_header_algorithm(token: str, expected_algorithm: str) -> None:
        """Reject tokens whose JOSE header does not match the configured algorithm."""
        try:
            header = jwt.get_unverified_header(token)
        except PyJwtInvalidTokenError as exc:
            raise InvalidTokenError("The delegated assistant token is malformed.") from exc

        actual_algorithm = header.get("alg")
        if actual_algorithm != expected_algorithm:
            raise InvalidTokenError("The delegated assistant token algorithm is not allowed.")

    def _normalize_claims(self, claims: dict[str, Any]) -> ValidatedAssistantClaims:
        """Map JWT payload fields into the internal trusted claims model."""
        try:
            customer_id = self._normalize_customer_id(claims)
            normalized = ValidatedAssistantClaims(
                session_id=self._required_string(claims, "jti"),
                customer_id=customer_id,
                scope_mode=self._required_string(claims, "scopeMode"),
                active_manufacturer_id=self._optional_string(claims.get("activeManufacturerId")),
                allowed_manufacturer_ids=claims.get("allowedManufacturerIds", []),
                assistant_scopes=claims.get("assistantScopes", []),
                issuer=self._required_string(claims, "iss"),
                audience=self._normalize_audience(claims.get("aud")),
                issued_at=self._datetime_from_epoch(claims.get("iat"), "iat"),
                expires_at=self._datetime_from_epoch(claims.get("exp"), "exp"),
                token_id=self._optional_string(claims.get("jti")),
            )
        except (TypeError, ValueError, ValidationError) as exc:
            raise InvalidTokenError("The delegated assistant token contains malformed claims.") from exc

        if normalized.audience != self.settings.assistant_jwt_audience:
            raise InvalidTokenError("The delegated assistant token audience is invalid.")

        return normalized

    @staticmethod
    def _required_string(claims: dict[str, Any], name: str) -> str:
        value = claims.get(name)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Missing required claim: {name}")
        return value.strip()

    @staticmethod
    def _normalize_customer_id(claims: dict[str, Any]) -> str:
        customer_claim = claims.get("customerId")
        subject_claim = claims.get("sub")

        if customer_claim is None:
            raise ValueError("Missing required claim: customerId")

        customer_id = str(customer_claim).strip()
        subject = str(subject_claim).strip() if subject_claim is not None else ""
        if not customer_id:
            raise ValueError("Missing required claim: customerId")
        if not subject:
            raise ValueError("Missing required claim: sub")
        if customer_id != subject:
            raise ValueError("Token subject does not match customerId.")

        return customer_id

    @staticmethod
    def _optional_string(value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Optional claim must be a string.")
        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _normalize_audience(value: Any) -> str:
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, list):
            normalized = [str(item).strip() for item in value if str(item).strip()]
            if len(normalized) == 1:
                return normalized[0]
        raise ValueError("Missing or malformed audience claim.")

    @staticmethod
    def _datetime_from_epoch(value: Any, claim_name: str) -> datetime:
        if value is None:
            raise ValueError(f"Missing required claim: {claim_name}")
        try:
            return datetime.fromtimestamp(int(value), tz=timezone.utc)
        except (TypeError, ValueError, OSError) as exc:
            raise ValueError(f"Malformed epoch claim: {claim_name}") from exc
