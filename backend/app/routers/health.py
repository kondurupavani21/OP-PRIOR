"""Health check router providing service readiness and diagnostic status."""
import time
from datetime import datetime, timezone
from fastapi import APIRouter, status
from app.core.config import settings
from app.database.session import check_db_health
from app.schemas.health import HealthCheckResponse

router = APIRouter(tags=["System Health"])

# Record start time for uptime calculation
START_TIME = time.time()


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Service Health Check",
    description="Inspects database connectivity, server uptime, and operational readiness.",
)
def get_health_status() -> HealthCheckResponse:
    """Perform health verification across critical dependencies."""
    is_db_healthy = check_db_health()
    uptime_seconds = round(time.time() - START_TIME, 2)

    db_status_text = "connected" if is_db_healthy else "unreachable"
    overall_status = "healthy" if is_db_healthy else "degraded"

    return HealthCheckResponse(
        status=overall_status,
        app_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        database=db_status_text,
        timestamp=datetime.now(timezone.utc),
        uptime_seconds=uptime_seconds,
        system_info={
            "debug": settings.DEBUG,
            "host": settings.HOST,
            "port": settings.PORT,
            "api_prefix": settings.API_V1_STR,
        },
    )
