"""Integration tests for Authentication & Role-Based Authorization."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.auth_service import seed_default_accounts

client = TestClient(app)


@pytest.fixture(autouse=True)
def ensure_seed_accounts():
    """Ensure seed accounts exist before tests run."""
    seed_default_accounts()


def test_seed_accounts_login():
    """Verify default seeded development accounts authenticate properly."""
    # Test Doctor login
    resp_doc = client.post("/api/v1/auth/login", json={
        "email": "doctor@medqueue.org",
        "password": "doctor123",
    })
    assert resp_doc.status_code == 200
    data_doc = resp_doc.json()
    assert "access_token" in data_doc
    assert data_doc["user"]["role"] == "Doctor"

    # Test Receptionist login
    resp_rec = client.post("/api/v1/auth/login", json={
        "email": "receptionist@medqueue.org",
        "password": "receptionist123",
    })
    assert resp_rec.status_code == 200
    assert resp_rec.json()["user"]["role"] == "Receptionist"

    # Test Admin login
    resp_adm = client.post("/api/v1/auth/login", json={
        "email": "admin@medqueue.org",
        "password": "admin123",
    })
    assert resp_adm.status_code == 200
    assert resp_adm.json()["user"]["role"] == "Admin"


def test_invalid_login():
    """Verify wrong password returns 401 Unauthorized."""
    resp = client.post("/api/v1/auth/login", json={
        "email": "doctor@medqueue.org",
        "password": "wrongpassword123",
    })
    assert resp.status_code == 401


def test_signup_and_profile():
    """Test registering a new doctor and retrieving /auth/me."""
    signup_payload = {
        "email": "newdoctor@hospital.org",
        "password": "securepass123",
        "full_name": "Dr. Arun Varma",
        "role": "Doctor",
        "department": "Cardiology",
    }
    signup_resp = client.post("/api/v1/auth/signup", json=signup_payload)
    assert signup_resp.status_code == 201
    user_data = signup_resp.json()
    assert user_data["email"] == "newdoctor@hospital.org"
    assert user_data["user_id"].startswith("USR-")

    # Login to obtain token
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "newdoctor@hospital.org",
        "password": "securepass123",
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    # Access /auth/me
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "newdoctor@hospital.org"


def test_unauthorized_access():
    """Verify /auth/me returns 401 when token is missing or malformed."""
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401

    resp_bad = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalidtoken123"})
    assert resp_bad.status_code == 401


def test_admin_role_restriction():
    """Verify only Admin can list all users."""
    # Login as receptionist
    rec_login = client.post("/api/v1/auth/login", json={
        "email": "receptionist@medqueue.org",
        "password": "receptionist123",
    })
    assert rec_login.status_code == 200
    rec_token = rec_login.json()["access_token"]

    # Receptionist attempts to access admin users endpoint
    resp_forbidden = client.get("/api/v1/auth/users", headers={"Authorization": f"Bearer {rec_token}"})
    assert resp_forbidden.status_code == 403

    # Admin access succeeds
    adm_login = client.post("/api/v1/auth/login", json={
        "email": "admin@medqueue.org",
        "password": "admin123",
    })
    assert adm_login.status_code == 200
    adm_token = adm_login.json()["access_token"]

    resp_allowed = client.get("/api/v1/auth/users", headers={"Authorization": f"Bearer {adm_token}"})
    assert resp_allowed.status_code == 200
    users = resp_allowed.json()
    assert len(users) >= 3
