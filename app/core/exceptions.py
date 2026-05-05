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
    """Raised when a runtime session cannot be found."""

    status_code = HTTPStatus.NOT_FOUND
    code = "session_not_found"
    message = "The runtime session was not found."


class SessionExpiredError(AppException):
    """Raised when a runtime session is no longer valid."""

    status_code = HTTPStatus.GONE
    code = "session_expired"
    message = "The runtime session has expired."


class SessionClosedError(AppException):
    """Raised when a closed runtime session is used."""

    status_code = HTTPStatus.CONFLICT
    code = "session_closed"
    message = "The runtime session is closed."


class VendorIntegrationError(AppException):
    """Raised when an external vendor integration fails."""

    status_code = HTTPStatus.BAD_GATEWAY
    code = "vendor_integration_error"
    message = "Vendor integration failed."


class DependencyUnavailableError(AppException):
    """Raised when a required service dependency is unavailable."""

    status_code = HTTPStatus.SERVICE_UNAVAILABLE
    code = "dependency_unavailable"
    message = "A required service dependency is unavailable."


class BackendClientError(AppException):
    """Raised when the internal VAM backend integration fails."""

    status_code = HTTPStatus.BAD_GATEWAY
    code = "backend_client_error"
    message = "Backend service call failed."


class BackendClientConfigurationError(BackendClientError):
    """Raised when the VAM backend client is not configured correctly."""

    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    code = "backend_client_configuration_error"
    message = "Backend client configuration is invalid."


class ConfigurationError(AppException):
    """Raised when service configuration is missing or invalid."""

    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    code = "configuration_error"
    message = "Service configuration is invalid."


class BackendClientNetworkError(BackendClientError):
    """Raised when the VAM backend cannot be reached."""

    code = "backend_client_network_error"
    message = "Backend service is unavailable."


class BackendClientTimeoutError(BackendClientNetworkError):
    """Raised when the VAM backend does not respond within the timeout."""

    code = "backend_client_timeout"
    message = "Backend service request timed out."


class BackendClientHTTPError(BackendClientError):
    """Raised when the VAM backend returns an unsuccessful HTTP status."""

    code = "backend_client_http_error"
    message = "Backend service returned an unsuccessful response."


class BackendClientResponseError(BackendClientError):
    """Raised when the VAM backend returns an invalid response shape."""

    code = "backend_client_response_error"
    message = "Backend service returned an invalid response."


class ToolExecutionError(AppException):
    """Raised when an assistant tool fails during execution."""

    status_code = HTTPStatus.BAD_GATEWAY
    code = "tool_execution_error"
    message = "Tool execution failed."


class UnknownToolError(AppException):
    """Raised when a requested tool is not registered."""

    status_code = HTTPStatus.NOT_FOUND
    code = "unknown_tool"
    message = "The requested tool is not registered."


class MissingToolScopeError(AuthorizationError):
    """Raised when the runtime session lacks a required assistant scope."""

    code = "missing_tool_scope"
    message = "The runtime session does not include the required tool scope."


class InvalidManufacturerAccessError(AuthorizationError):
    """Raised when a tool request violates manufacturer scoping."""

    code = "invalid_manufacturer_access"
    message = "The requested manufacturer is outside the runtime session scope."


class InvalidToolInputError(AppException):
    """Raised when tool input fails validation."""

    status_code = HTTPStatus.UNPROCESSABLE_ENTITY
    code = "invalid_tool_input"
    message = "Tool input validation failed."


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
