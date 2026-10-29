"""API Routers package."""
from app.routers.health import router as health_router
from app.routers.triage import router as triage_router
from app.routers.patients import router as patients_router
from app.routers.encounters import router as encounters_router
from app.routers.documents import router as documents_router
from app.routers.medical_history import router as medical_history_router
from app.routers.queue import router as queue_router
from app.routers.consultations import router as consultations_router
from app.routers.auth import router as auth_router
from app.routers.stats import router as stats_router
from app.routers.models import router as models_router
from app.routers.summaries import router as summaries_router
from app.routers.simulation import router as simulation_router
from app.routers.announcements import router as announcements_router
from app.routers.previous_consultations import router as previous_consultations_router

__all__ = [
    "health_router",
    "triage_router",
    "patients_router",
    "encounters_router",
    "documents_router",
    "medical_history_router",
    "queue_router",
    "consultations_router",
    "auth_router",
    "stats_router",
    "models_router",
    "summaries_router",
    "simulation_router",
    "announcements_router",
    "previous_consultations_router",
]

