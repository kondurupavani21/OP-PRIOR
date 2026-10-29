"""Health check response schema."""
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class HealthCheckResponse(BaseModel):
    """Schema representing the backend health status."""
    status: str = Field(default="healthy", description="Application status: healthy or degraded")
    app_name: str = Field(description="Name of the backend service")
    version: str = Field(description="Semantic version of the API")
    environment: str = Field(description="Current deployment environment (development/production)")
    database: str = Field(description="Database connectivity status: connected or unreachable")
    timestamp: datetime = Field(description="UTC timestamp of the health check inspection")
    uptime_seconds: float = Field(description="Seconds elapsed since server boot")
    system_info: Optional[Dict[str, Any]] = Field(default=None, description="Optional system runtime metrics")
