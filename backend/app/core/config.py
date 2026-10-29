"""Application Settings and Configuration."""
from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base backend directory
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE_PATH = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """Core application settings loaded from environment or .env file."""

    # Project metadata
    PROJECT_NAME: str = "MedQueue AI Backend"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Server binding
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    API_V1_STR: str = "/api/v1"

    # CORS Configuration
    BACKEND_CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]

    # Database Configuration (MongoDB Primary)
    DATABASE_URL: str = "sqlite:///./medqueue.db"  # Retained for backwards compatibility
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "medqueue_ai"
    USE_MONGOMOCK: bool = False  # Set to True or auto-fallback if local mongod is not running

    # Security & Tokens
    SECRET_KEY: str = "medqueue-dev-secret-key-1234567890-secure"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Medical Document Storage & OCR Configuration
    MAX_UPLOAD_SIZE_MB: int = 15
    UPLOAD_DIR: str = "uploads/documents"
    ENABLE_TESSERACT_OCR: bool = True

    # AI Summarization & LLM Provider Configuration
    LLM_PROVIDER: str = "mock"  # mock, openai, ollama
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_PATH),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Convert comma-separated string to a list of allowed origin URLs."""
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                # Handle raw JSON-like string if passed
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, (list, tuple)):
            return list(v)
        return []

    @property
    def cors_origins_list(self) -> List[str]:
        """Convenience property returning origins as Python list."""
        if isinstance(self.BACKEND_CORS_ORIGINS, list):
            return self.BACKEND_CORS_ORIGINS
        return [str(self.BACKEND_CORS_ORIGINS)]


# Singleton instance
settings = Settings()
