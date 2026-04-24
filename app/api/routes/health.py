"""Health check route for service and container probes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.models.common import HealthResponse


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Return a minimal health response for load balancers and readiness checks."""
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.app_env,
        timestamp=datetime.now(timezone.utc),
    )
