"""Convenient runner script for MedQueue AI FastAPI backend."""
import sys
import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    print(f"Starting {settings.PROJECT_NAME} on http://{settings.HOST}:{settings.PORT}")
    print(f"Interactive Swagger Documentation: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"Health-Check Endpoint: http://{settings.HOST}:{settings.PORT}/health")
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
