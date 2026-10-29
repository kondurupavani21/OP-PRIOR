"""MongoDB-backed Authentication, Role-Based Access Control, and Account Service."""
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from app.database.mongodb import get_users_col, get_audit_events_col
from app.schemas.auth import UserCreate, UserResponse
from app.core.security import get_password_hash, verify_password


def utc_iso_now() -> str:
    """Return timezone-aware ISO string for current UTC time."""
    return datetime.now(timezone.utc).isoformat()


def seed_default_accounts():
    """Seed standard development accounts for Doctor, Receptionist, and Admin."""
    col = get_users_col()
    default_accounts = [
        {
            "user_id": "USR-DOC-001",
            "email": "doctor@medqueue.org",
            "full_name": "Dr. Sarah Rao, MD",
            "password": "doctor123",
            "role": "Doctor",
            "department": "General Medicine",
        },
        {
            "user_id": "USR-REC-001",
            "email": "receptionist@medqueue.org",
            "full_name": "Priya Sharma",
            "password": "receptionist123",
            "role": "Receptionist",
            "department": "Patient Registration",
        },
        {
            "user_id": "USR-ADM-001",
            "email": "admin@medqueue.org",
            "full_name": "System Administrator",
            "password": "admin123",
            "role": "Admin",
            "department": "Clinical Informatics",
        },
    ]

    for acc in default_accounts:
        if not col.find_one({"email": acc["email"]}):
            col.insert_one({
                "user_id": acc["user_id"],
                "email": acc["email"],
                "full_name": acc["full_name"],
                "hashed_password": get_password_hash(acc["password"]),
                "role": acc["role"],
                "department": acc["department"],
                "is_active": True,
                "created_at": utc_iso_now(),
            })


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Retrieve user record from MongoDB by email."""
    col = get_users_col()
    return col.find_one({"email": email.lower().strip()})


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve user record from MongoDB by user_id."""
    col = get_users_col()
    return col.find_one({"user_id": user_id})


def create_user(payload: UserCreate) -> UserResponse:
    """Register a new user in MongoDB with role assignment."""
    col = get_users_col()
    clean_email = payload.email.lower().strip()

    if col.find_one({"email": clean_email}):
        raise ValueError(f"User with email '{payload.email}' already exists.")

    assigned_id = f"USR-{uuid.uuid4().hex[:8].upper()}"
    now_iso = utc_iso_now()

    doc = {
        "user_id": assigned_id,
        "email": clean_email,
        "full_name": payload.full_name.strip(),
        "hashed_password": get_password_hash(payload.password),
        "role": payload.role or "Doctor",
        "department": payload.department or "General Medicine",
        "is_active": True,
        "created_at": now_iso,
    }
    col.insert_one(doc)

    # Log audit event
    get_audit_events_col().insert_one({
        "audit_id": f"AUD-{uuid.uuid4().hex[:10]}",
        "action": "USER_CREATED",
        "user_id": assigned_id,
        "user_role": doc["role"],
        "timestamp": now_iso,
        "details": f"Registered user {doc['email']} with role {doc['role']}",
    })

    return UserResponse(
        user_id=doc["user_id"],
        email=doc["email"],
        full_name=doc["full_name"],
        role=doc["role"],
        department=doc["department"],
        is_active=doc["is_active"],
        created_at=doc["created_at"],
    )


def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Verify email and password against MongoDB user store."""
    user = get_user_by_email(email)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    if not user.get("is_active", True):
        return None
    return user


def list_users(role: Optional[str] = None) -> List[UserResponse]:
    """List system users with optional role filter."""
    col = get_users_col()
    query = {"role": role} if role else {}
    results: List[UserResponse] = []
    for doc in col.find(query):
        results.append(UserResponse(
            user_id=doc["user_id"],
            email=doc["email"],
            full_name=doc["full_name"],
            role=doc["role"],
            department=doc["department"],
            is_active=doc.get("is_active", True),
            created_at=doc.get("created_at", utc_iso_now()),
        ))
    return results
