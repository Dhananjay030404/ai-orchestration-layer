"""Application exception hierarchy and HTTP mapping helpers."""

from http import HTTPStatus
from typing import Any


class AppException(Exception):
    """Base exception for expected application failures."""

    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR
    code: str = "application_error"
    message: str = "Application error."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.status_code = status_code or self.status_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(AppException):
    """Raised when a caller cannot be authenticated."""

    status_code = HTTPStatus.UNAUTHORIZED
    code = "authentication_failed"
    message = "Authentication failed."


class AuthorizationError(AppException):
    """Raised when an authenticated caller lacks required permissions."""

    status_code = HTTPStatus.FORBIDDEN
    code = "authorization_failed"
    message = "The caller is not authorized to perform this action."


class InvalidTokenError(AuthenticationError):
    """Raised when a delegated assistant token cannot be trusted."""

    code = "invalid_token"
    message = "The delegated assistant token is invalid."


class ExpiredTokenError(InvalidTokenError):
    """Raised when a delegated assistant token is expired."""

    code = "expired_token"
    message = "The delegated assistant token has expired."


class SessionNotFoundError(AppException):
    """Raised when an orchestration session cannot be found."""

    status_code = HTTPStatus.NOT_FOUND
    code = "session_not_found"
    message = "The orchestration session was not found."


class SessionExpiredError(AppException):
    """Raised when an orchestration session is no longer valid."""

    status_code = HTTPStatus.GONE
    code = "session_expired"
    message = "The orchestration session has expired."


class SessionClosedError(AppException):
    """Raised when a closed orchestration session is used."""

    status_code = HTTPStatus.CONFLICT
    code = "session_closed"
    message = "The orchestration session is closed."


class VendorIntegrationError(AppException):
    """Raised when an external vendor integration fails."""

    status_code = HTTPStatus.BAD_GATEWAY
    code = "vendor_integration_error"
    message = "Vendor integration failed."


class BackendClientError(AppException):
    """Raised when the internal VAM backend integration fails."""

    status_code = HTTPStatus.BAD_GATEWAY
    code = "backend_client_error"
    message = "Backend service call failed."


class ToolExecutionError(AppException):
    """Raised when an orchestration tool fails during execution."""

    status_code = HTTPStatus.BAD_GATEWAY
    code = "tool_execution_error"
    message = "Tool execution failed."


def http_status_for_exception(exc: AppException) -> int:
    """Return the HTTP status code for an application exception."""
    return int(exc.status_code)


def error_payload_for_exception(exc: AppException) -> dict[str, Any]:
    """Return a serializable error body fragment for an application exception."""
    return {
        "code": exc.code,
        "message": exc.message,
        "details": exc.details,
    }


class NotFoundError(AppException):
    """Compatibility exception for generic resource lookups."""

    status_code = HTTPStatus.NOT_FOUND
    code = "not_found"
    message = "The requested resource was not found."

    def __init__(self, resource: str, resource_id: str) -> None:
        super().__init__(
            f"{resource} was not found.",
            details={"resource": resource, "resource_id": resource_id},
        )


class TokenValidationError(InvalidTokenError):
    """Compatibility exception for existing token validation code."""


class ExternalServiceError(VendorIntegrationError):
    """Compatibility exception for existing external dependency code."""

    def __init__(self, service_name: str, message: str = "External service call failed.") -> None:
        super().__init__(message, details={"service": service_name})


AppError = AppException
