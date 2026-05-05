"""Health check route for service and container probes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.core.exceptions import DependencyUnavailableError
from app.models.common import HealthResponse
from app.repositories.session_repository import check_session_repository


router = APIRouter(tags=["health"])


async def get_health_settings() -> Settings:
    """Provide settings without sending the dependency through a worker thread."""
    return get_settings()


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(get_health_settings)) -> HealthResponse:
    """Return a minimal health response for load balancers and readiness checks."""
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.app_env,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/ready", response_model=HealthResponse)
async def readiness_check(settings: Settings = Depends(get_health_settings)) -> HealthResponse:
    """Return readiness only when required persistence is reachable."""
    try:
        await check_session_repository()
    except Exception as exc:
        raise DependencyUnavailableError(
            "Required persistence dependency is unavailable.",
            details={"dependency": "mysql"},
        ) from exc

    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.app_env,
        timestamp=datetime.now(timezone.utc),
    )
