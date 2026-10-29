"""MongoDB Database Client and Collections Manager for MedQueue AI.

Provides resilient connection management with automated fallback to mongomock
when an external MongoDB instance is not available.
"""
import logging
from typing import Optional, Any
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from app.core.config import settings

logger = logging.getLogger("medqueue.mongodb")

_client_instance: Optional[Any] = None
_db_instance: Optional[Database] = None
_is_mock: bool = False


def get_mongo_client() -> Any:
    """Retrieve or initialize MongoDB client with resilient fallback."""
    global _client_instance, _is_mock

    if _client_instance is not None:
        return _client_instance

    if settings.USE_MONGOMOCK:
        logger.info("USE_MONGOMOCK is enabled. Initializing in-memory MongoMock client.")
        import mongomock
        _client_instance = mongomock.MongoClient()
        _is_mock = True
        return _client_instance

    try:
        logger.info(f"Connecting to MongoDB at {settings.MONGODB_URL} (timeout 1.5s)...")
        real_client = MongoClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=1500,
            connectTimeoutMS=1500,
        )
        # Verify server connection
        real_client.admin.command("ping")
        logger.info("Successfully connected to live MongoDB daemon.")
        _client_instance = real_client
        _is_mock = False
        return _client_instance
    except (ConnectionFailure, ServerSelectionTimeoutError, Exception) as exc:
        logger.warning(
            f"Live MongoDB not accessible at {settings.MONGODB_URL} ({exc}). "
            "Falling back seamlessly to in-memory MongoMock for local execution."
        )
        import mongomock
        _client_instance = mongomock.MongoClient()
        _is_mock = True
        return _client_instance


def get_mongodb() -> Database:
    """Get the active MongoDB database object."""
    global _db_instance
    if _db_instance is not None:
        return _db_instance

    client = get_mongo_client()
    _db_instance = client[settings.MONGODB_DB_NAME]
    return _db_instance


def is_mongomock_active() -> bool:
    """Check if in-memory MongoMock is being used."""
    get_mongo_client()
    return _is_mock


# =========================================================================
# Collection Accessors (12 Dedicated Domain Collections)
# =========================================================================

def get_users_col():
    return get_mongodb()["users"]

def get_patients_col():
    return get_mongodb()["patients"]

def get_encounters_col():
    return get_mongodb()["encounters"]

def get_medical_documents_col():
    return get_mongodb()["medical_documents"]

def get_medical_history_col():
    return get_mongodb()["medical_history"]

def get_triage_assessments_col():
    return get_mongodb()["triage_assessments"]

def get_queue_entries_col():
    return get_mongodb()["queue_entries"]

def get_doctor_overrides_col():
    return get_mongodb()["doctor_overrides"]

def get_ai_summaries_col():
    return get_mongodb()["ai_summaries"]

def get_model_predictions_col():
    return get_mongodb()["model_predictions"]

def get_announcement_events_col():
    return get_mongodb()["announcement_events"]

def get_audit_events_col():
    return get_mongodb()["audit_events"]

def get_previous_consultations_col():
    return get_mongodb()["previous_consultations"]

def get_document_extractions_col():
    return get_mongodb()["document_extractions"]


def init_mongodb_indexes():
    """Create essential performance and uniqueness indexes across collections."""
    db = get_mongodb()
    try:
        # Users
        db["users"].create_index([("email", ASCENDING)], unique=True)
        db["users"].create_index([("role", ASCENDING)])

        # Patients
        db["patients"].create_index([("patient_code", ASCENDING)], unique=True)
        db["patients"].create_index([("contact", ASCENDING)])
        db["patients"].create_index([("full_name", ASCENDING)])

        # Encounters
        db["encounters"].create_index([("encounter_id", ASCENDING)], unique=True)
        db["encounters"].create_index([("patient_id", ASCENDING)])
        db["encounters"].create_index([("patient_code", ASCENDING)])
        db["encounters"].create_index([("arrival_time", DESCENDING)])
        db["encounters"].create_index([("status", ASCENDING)])

        # Medical Documents
        db["medical_documents"].create_index([("document_id", ASCENDING)], unique=True)
        db["medical_documents"].create_index([("patient_id", ASCENDING)])
        db["medical_documents"].create_index([("patient_code", ASCENDING)])
        db["medical_documents"].create_index([("verification_status", ASCENDING)])
        db["medical_documents"].create_index([("identity_match_status", ASCENDING)])

        # Document Extractions
        db["document_extractions"].create_index([("document_id", ASCENDING)], unique=True)
        db["document_extractions"].create_index([("patient_code", ASCENDING)])

        # Previous Consultations
        db["previous_consultations"].create_index([("consultation_id", ASCENDING)], unique=True)
        db["previous_consultations"].create_index([("patient_code", ASCENDING)])
        db["previous_consultations"].create_index([("consultation_date", DESCENDING)])

        # Medical History
        db["medical_history"].create_index([("history_id", ASCENDING)], unique=True)
        db["medical_history"].create_index([("patient_id", ASCENDING)])
        db["medical_history"].create_index([("patient_code", ASCENDING)])

        # Triage Assessments
        db["triage_assessments"].create_index([("assessment_id", ASCENDING)], unique=True)
        db["triage_assessments"].create_index([("encounter_id", ASCENDING)])

        # Queue Entries
        db["queue_entries"].create_index([("entry_id", ASCENDING)], unique=True)
        db["queue_entries"].create_index([("token_number", ASCENDING)])
        db["queue_entries"].create_index([("queue_status", ASCENDING)])
        db["queue_entries"].create_index([("clinician_approved_priority", ASCENDING)])

        # Doctor Overrides
        db["doctor_overrides"].create_index([("override_id", ASCENDING)], unique=True)
        db["doctor_overrides"].create_index([("encounter_id", ASCENDING)])

        # AI Summaries
        db["ai_summaries"].create_index([("summary_id", ASCENDING)], unique=True)
        db["ai_summaries"].create_index([("encounter_id", ASCENDING)], unique=True)
        db["ai_summaries"].create_index([("patient_id", ASCENDING)])

        # Audit Events
        db["audit_events"].create_index([("audit_id", ASCENDING)], unique=True)
        db["audit_events"].create_index([("timestamp", DESCENDING)])

        logger.info("MongoDB domain collections and indexes successfully initialized.")

        try:
            from app.services.auth_service import seed_default_accounts
            seed_default_accounts()
        except Exception as seed_err:
            logger.warning(f"Note on seeding accounts: {seed_err}")
    except Exception as exc:
        logger.warning(f"Note on MongoDB index initialization: {exc}")
