"""Application exception types mapped to the standard error model."""

from typing import Any


class AppError(Exception):
    """Base exception for expected application failures."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        status_code: int,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class TokenValidationError(AppError):
    """Raised when a delegated assistant token cannot be trusted."""

    def __init__(self, message: str = "Delegated assistant token validation failed.") -> None:
        super().__init__(message, code="token_validation_failed", status_code=401)


class AuthorizationError(AppError):
    """Raised when the validated principal lacks required permissions."""

    def __init__(self, message: str = "The delegated principal is not authorized.") -> None:
        super().__init__(message, code="authorization_failed", status_code=403)


class NotFoundError(AppError):
    """Raised when a requested resource cannot be found."""

    def __init__(self, resource: str, resource_id: str) -> None:
        super().__init__(
            f"{resource} was not found.",
            code="not_found",
            status_code=404,
            details={"resource": resource, "resource_id": resource_id},
        )


class ExternalServiceError(AppError):
    """Raised when a controlled external dependency call fails."""

    def __init__(self, service_name: str, message: str = "External service call failed.") -> None:
        super().__init__(
            message,
            code="external_service_error",
            status_code=502,
            details={"service": service_name},
        )
