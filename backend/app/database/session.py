"""Database engine, session factory, dependency, and health checks."""
import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.database.base import Base

logger = logging.getLogger("medqueue.database")

# Handle SQLite-specific connect args
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency to provide a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables."""
    try:
        # Import models to ensure they are registered with Base.metadata
        from app.database import models  # noqa: F401
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified and initialized successfully.")
    except Exception as exc:
        logger.error(f"Error initializing database tables: {exc}")
        raise


def check_db_health() -> bool:
    """Run a lightweight query to verify active database connectivity."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error(f"Database health check failed: {exc}")
        return False
