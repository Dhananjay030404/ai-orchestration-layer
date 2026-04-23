"""FastAPI application bootstrap for the VAM AI agent service."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes import health, runtime, session, tools, webhook
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging
from app.models.common import ErrorDetail, ErrorResponse


logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI app."""
    settings = get_settings()
    configure_logging(settings.log_level, settings.service_name)

    app = FastAPI(
        title=settings.service_name,
        version="0.1.0",
        description="Secure Python orchestration service for the VAM assistant platform.",
    )

    register_exception_handlers(app)
    register_routers(app, settings.api_prefix)
    return app


def register_routers(app: FastAPI, api_prefix: str) -> None:
    """Register all API routers, including placeholders for future integrations."""
    app.include_router(health.router, prefix=api_prefix)
    app.include_router(session.router, prefix=api_prefix)
    app.include_router(runtime.router, prefix=api_prefix)
    app.include_router(tools.router, prefix=api_prefix)
    app.include_router(webhook.router, prefix=api_prefix)


def register_exception_handlers(app: FastAPI) -> None:
    """Install a consistent API error envelope."""

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return build_error_response(
            request=request,
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            details=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return build_error_response(
            request=request,
            status_code=422,
            code="validation_error",
            message="Request validation failed.",
            details={"errors": jsonable_encoder(exc.errors())},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled application error", exc_info=exc)
        return build_error_response(
            request=request,
            status_code=500,
            code="internal_server_error",
            message="An unexpected error occurred.",
            details={},
        )


def build_error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any],
) -> JSONResponse:
    """Build the standard error response payload."""
    trace_id = request.headers.get("x-request-id") or request.headers.get("x-correlation-id")
    payload = ErrorResponse(
        error=ErrorDetail(code=code, message=message, details=details),
        trace_id=trace_id,
    )
    return JSONResponse(status_code=status_code, content=jsonable_encoder(payload))


app = create_app()
