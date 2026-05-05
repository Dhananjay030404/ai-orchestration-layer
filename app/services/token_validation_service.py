"""Delegated assistant token validation service."""

import base64
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import jwt
from jwt import ExpiredSignatureError, InvalidAudienceError, InvalidIssuerError
from jwt import InvalidSignatureError
from jwt import InvalidTokenError as PyJwtInvalidTokenError
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationError, ExpiredTokenError, InvalidTokenError
from app.models.session import RuntimeSession, RuntimeToolClaims, ValidatedAssistantClaims


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

    async def validate_runtime_tool_token(self, token: str) -> RuntimeToolClaims:
        """Validate a Python-issued runtime tool token."""
        return self.validate_runtime_tool_token_sync(token)

    def mint_runtime_tool_token(self, session: RuntimeSession) -> str:
        """Mint a short-lived token that lets the assistant runtime call Python tools."""
        signing_key = self._primary_signing_key()
        if not signing_key:
            raise AuthenticationError("Runtime tool token signing is not configured.")

        now = datetime.now(timezone.utc)
        payload = {
            "iss": self._runtime_token_issuer,
            "aud": self.settings.assistant_jwt_audience,
            "sub": session.customer_id,
            "jti": str(uuid4()),
            "iat": int(now.timestamp()),
            "exp": int(session.expires_at.timestamp()),
            "tokenUse": "runtime_tool",
            "runtimeSessionId": session.runtime_session_id,
            "assistantSessionId": session.assistant_session_id,
            "customerId": session.customer_id,
        }
        return jwt.encode(payload, signing_key, algorithm=self.settings.assistant_jwt_algorithm)

    def validate_assistant_token_sync(self, token: str) -> ValidatedAssistantClaims:
        """Synchronously validate a JWT for unit tests and non-async callers."""
        if not token or not token.strip():
            raise AuthenticationError("A delegated assistant token is required.")

        if not self.settings.assistant_jwt_secret:
            raise AuthenticationError("Delegated assistant token validation is not configured.")

        issuer = self.settings.assistant_jwt_issuer
        if not issuer:
            raise AuthenticationError("Delegated assistant token issuer is not configured.")

        expected_algorithm = self.settings.assistant_jwt_algorithm
        self._validate_header_algorithm(token, expected_algorithm)

        try:
            raw_claims = self._decode_with_configured_keys(
                token,
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

    def validate_runtime_tool_token_sync(self, token: str) -> RuntimeToolClaims:
        """Synchronously validate a Python-issued runtime tool JWT."""
        if not token or not token.strip():
            raise AuthenticationError("A runtime tool token is required.")

        if not self.settings.assistant_jwt_secret:
            raise AuthenticationError("Runtime tool token validation is not configured.")

        expected_algorithm = self.settings.assistant_jwt_algorithm
        self._validate_header_algorithm(token, expected_algorithm)

        try:
            raw_claims = self._decode_with_configured_keys(
                token,
                algorithms=[expected_algorithm],
                audience=self.settings.assistant_jwt_audience,
                issuer=self._runtime_token_issuer,
                options={
                    "require": [
                        "exp",
                        "iat",
                        "iss",
                        "aud",
                        "sub",
                        "jti",
                        "tokenUse",
                        "runtimeSessionId",
                        "assistantSessionId",
                        "customerId",
                    ]
                },
            )
        except ExpiredSignatureError as exc:
            raise ExpiredTokenError("The runtime tool token has expired.") from exc
        except (InvalidAudienceError, InvalidIssuerError, PyJwtInvalidTokenError) as exc:
            raise InvalidTokenError("The runtime tool token is invalid.") from exc

        return self._normalize_runtime_tool_claims(raw_claims)

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

    def _decode_with_configured_keys(
        self,
        token: str,
        *,
        algorithms: list[str],
        audience: str,
        issuer: str,
        options: dict[str, Any],
    ) -> dict[str, Any]:
        """Decode a JWT using common HMAC secret encodings used by Java backends."""
        last_signature_error: InvalidSignatureError | None = None

        for key in self._signing_key_candidates():
            try:
                return jwt.decode(
                    token,
                    key,
                    algorithms=algorithms,
                    audience=audience,
                    issuer=issuer,
                    options=options,
                )
            except InvalidSignatureError as exc:
                last_signature_error = exc

        if last_signature_error is not None:
            raise last_signature_error

        raise InvalidTokenError("No JWT signing key candidates are configured.")

    def _primary_signing_key(self) -> str | bytes | None:
        """Return the preferred key for Python-issued runtime tool tokens."""
        return next(iter(self._signing_key_candidates()), None)

    def _signing_key_candidates(self) -> list[str | bytes]:
        """Return unique secret interpretations without exposing configured values."""
        secret = self.settings.assistant_jwt_secret
        if not secret:
            return []

        candidates: list[str | bytes] = [secret]
        candidates.extend(self._decoded_secret_candidates(secret))

        unique: list[str | bytes] = []
        seen: set[tuple[str, str | bytes]] = set()
        for candidate in candidates:
            marker = (
                "bytes" if isinstance(candidate, bytes) else "str",
                candidate if isinstance(candidate, bytes) else candidate.encode("utf-8"),
            )
            if marker in seen:
                continue
            seen.add(marker)
            unique.append(candidate)
        return unique

    @staticmethod
    def _decoded_secret_candidates(secret: str) -> list[bytes]:
        """Decode optional base64/url-safe-base64/hex encoded HMAC secrets."""
        candidates: list[bytes] = []
        normalized = secret.strip()
        padded = normalized + ("=" * (-len(normalized) % 4))

        for decoder in (base64.b64decode, base64.urlsafe_b64decode):
            try:
                decoded = decoder(padded)
            except (ValueError, TypeError):
                continue
            if decoded:
                candidates.append(decoded)

        try:
            decoded_hex = bytes.fromhex(normalized)
        except ValueError:
            decoded_hex = b""
        if decoded_hex:
            candidates.append(decoded_hex)

        return candidates

    def _normalize_claims(self, claims: dict[str, Any]) -> ValidatedAssistantClaims:
        """Map JWT payload fields into the internal trusted claims model."""
        try:
            customer_id = self._normalize_customer_id(claims)
            normalized = ValidatedAssistantClaims(
                session_id=self._required_string(claims, "jti"),
                customer_id=customer_id,
                scope_mode=self._required_string(claims, "scopeMode"),
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

    def _normalize_runtime_tool_claims(self, claims: dict[str, Any]) -> RuntimeToolClaims:
        """Map Python-issued runtime tool JWT payload into trusted claims."""
        try:
            if claims.get("tokenUse") != "runtime_tool":
                raise ValueError("Token is not a runtime tool token.")
            customer_id = self._normalize_customer_id(claims)
            normalized = RuntimeToolClaims(
                token_id=self._required_string(claims, "jti"),
                tokenUse="runtime_tool",
                runtimeSessionId=self._required_string(claims, "runtimeSessionId"),
                assistantSessionId=self._required_string(claims, "assistantSessionId"),
                customerId=customer_id,
                issuer=self._required_string(claims, "iss"),
                audience=self._normalize_audience(claims.get("aud")),
                issued_at=self._datetime_from_epoch(claims.get("iat"), "iat"),
                expires_at=self._datetime_from_epoch(claims.get("exp"), "exp"),
            )
        except (TypeError, ValueError, ValidationError) as exc:
            raise InvalidTokenError("The runtime tool token contains malformed claims.") from exc

        if normalized.audience != self.settings.assistant_jwt_audience:
            raise InvalidTokenError("The runtime tool token audience is invalid.")
        if normalized.issuer != self._runtime_token_issuer:
            raise InvalidTokenError("The runtime tool token issuer is invalid.")

        return normalized

    @property
    def _runtime_token_issuer(self) -> str:
        return self.settings.app_name

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
