"""Security dependencies for delegated assistant token boundaries."""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import TokenValidationError


bearer_scheme = HTTPBearer(auto_error=False)


async def require_delegated_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    """Require a bearer token without trusting provider-supplied identities."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise TokenValidationError("A delegated assistant bearer token is required.")

    if not credentials.credentials:
        raise TokenValidationError("The delegated assistant bearer token is empty.")

    return credentials.credentials
