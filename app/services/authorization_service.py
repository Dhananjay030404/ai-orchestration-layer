"""Authorization checks over already-validated delegated principal claims."""

from app.core.exceptions import AuthorizationError
from app.models.session import ValidatedAssistantClaims


class AuthorizationService:
    """Evaluate permissions issued by the Spring Boot backend."""

    def require_permissions(
        self,
        principal: ValidatedAssistantClaims,
        required_permissions: list[str],
    ) -> None:
        """Require all permissions declared by a tool contract."""
        missing = set(required_permissions) - set(principal.permissions)
        if missing:
            raise AuthorizationError("The delegated principal lacks required tool permissions.")
