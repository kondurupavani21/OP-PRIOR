"""Pytest configuration and test isolation fixtures."""
import pytest
from app.database.mongodb import get_mongodb
from app.services.auth_service import seed_default_accounts


@pytest.fixture(autouse=True)
def clean_test_state():
    """Ensure clean test state across database collections and default accounts."""
    db = get_mongodb()
    # Reset transient operational collections
    db["queue_entries"].delete_many({})
    db["announcement_events"].delete_many({})
    db["doctor_overrides"].delete_many({})
    db["ai_summaries"].delete_many({})
    db["patients"].delete_many({})
    db["encounters"].delete_many({})
    db["medical_history"].delete_many({})
    db["medical_documents"].delete_many({})
    
    # Remove test-generated users and encounters
    db["users"].delete_many({"email": {"$nin": ["doctor@medqueue.org", "receptionist@medqueue.org", "nurse@medqueue.org"]}})
    seed_default_accounts()
    yield
