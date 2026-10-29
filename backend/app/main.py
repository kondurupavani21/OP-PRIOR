"""FastAPI Application Entry Point for MedQueue AI."""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.database.session import init_db
from app.routers import (
    health_router,
    triage_router,
    patients_router,
    encounters_router,
    documents_router,
    medical_history_router,
    queue_router,
    consultations_router,
    auth_router,
    stats_router,
    models_router,
    summaries_router,
    simulation_router,
    announcements_router,
    previous_consultations_router,
)
from app.database.mongodb import init_mongodb_indexes


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("medqueue.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle hooks: initialize database and verify startup state."""
    logger.info("Initializing MedQueue AI Database schema & MongoDB collections...")
    init_db()
    init_mongodb_indexes()
    from app.services.auth_service import seed_default_accounts
    seed_default_accounts()
    logger.info(f"Loaded CORS origins: {settings.cors_origins_list}")
    logger.info(f"{settings.PROJECT_NAME} v{settings.VERSION} ready.")
    yield
    logger.info("MedQueue AI Backend shutting down...")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Intelligent Clinical Triage and Dynamic Outpatient Queue Orchestration API for MedQueue AI.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# =========================================================================
# CORS Middleware Configuration (React + Vite Frontend Integration)
# =========================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================================
# Health Check Endpoints (Root & API Prefix)
# =========================================================================
app.include_router(health_router)  # Provides GET /health
app.include_router(health_router, prefix=settings.API_V1_STR)  # Provides GET /api/v1/health

# =========================================================================
# API v1 Domain Routers
# =========================================================================
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(triage_router, prefix=settings.API_V1_STR)
app.include_router(patients_router, prefix=settings.API_V1_STR)
app.include_router(encounters_router, prefix=settings.API_V1_STR)
app.include_router(documents_router, prefix=settings.API_V1_STR)
app.include_router(medical_history_router, prefix=settings.API_V1_STR)
app.include_router(queue_router, prefix=settings.API_V1_STR)
app.include_router(consultations_router, prefix=settings.API_V1_STR)
app.include_router(stats_router, prefix=settings.API_V1_STR)
app.include_router(models_router, prefix=settings.API_V1_STR)
app.include_router(summaries_router, prefix=settings.API_V1_STR)
app.include_router(simulation_router, prefix=settings.API_V1_STR)
app.include_router(announcements_router, prefix=settings.API_V1_STR)
app.include_router(previous_consultations_router, prefix=settings.API_V1_STR)



@app.get("/", tags=["Root"])
def root_index():
    """Root entrypoint with service pointers."""
    return {
        "message": "Welcome to MedQueue AI API Server",
        "version": settings.VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "health_check": "/health",
        "api_v1": settings.API_V1_STR,
    }
