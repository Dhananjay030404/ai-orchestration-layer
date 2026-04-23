"""Shared API models used across routes and services."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    """Base model with API-friendly serialization defaults."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ErrorDetail(ApiModel):
    """Single structured error object."""

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(ApiModel):
    """Standard error envelope returned by every exception handler."""

    error: ErrorDetail
    trace_id: str | None = None


class HealthResponse(ApiModel):
    """Response returned by the health endpoint."""

    status: str
    service: str
    environment: str
    timestamp: datetime


class DelegatedPrincipal(ApiModel):
    """Identity and authorization claims from a validated delegated token."""

    subject: str
    customer_id: str
    manufacturer_id: str | None = None
    scopes: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None
    token_id: str | None = None
    raw_claims: dict[str, Any] = Field(default_factory=dict)
