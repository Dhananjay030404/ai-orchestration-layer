"""Security helpers for delegated assistant token boundaries."""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import AuthenticationError


bearer_scheme = HTTPBearer(auto_error=False)


def extract_bearer_token(authorization_header: str | None) -> str:
    """Extract a Bearer token from an Authorization header value."""
    if not authorization_header or not authorization_header.strip():
        raise AuthenticationError("Authorization header is required.")

    scheme, separator, token = authorization_header.strip().partition(" ")
    if not separator or scheme.lower() != "bearer" or not token.strip():
        raise AuthenticationError("Authorization header must use the Bearer scheme.")

    if " " in token.strip():
        raise AuthenticationError("Bearer token must not contain spaces.")

    return token.strip()


async def require_delegated_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    """Return the delegated Bearer token from FastAPI credentials."""
    if credentials is None:
        raise AuthenticationError("Authorization header is required.")

    return extract_bearer_token(f"{credentials.scheme} {credentials.credentials}")
