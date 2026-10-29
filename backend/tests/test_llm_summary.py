"""Test Suite for LLM Doctor Decision Support & Grounded Clinical Summaries."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

from app.services.auth_service import seed_default_accounts

client = TestClient(app)


@pytest.fixture(autouse=True)
def ensure_seed_accounts():
    """Ensure seed accounts exist before tests run."""
    seed_default_accounts()


@pytest.fixture
def auth_tokens():
    """Obtain access tokens for doctor and receptionist accounts."""
    doc_resp = client.post("/api/v1/auth/login", json={"email": "doctor@medqueue.org", "password": "doctor123"})
    rec_resp = client.post("/api/v1/auth/login", json={"email": "receptionist@medqueue.org", "password": "receptionist123"})
    return {
        "doctor": doc_resp.json()["access_token"],
        "receptionist": rec_resp.json()["access_token"],
    }


def test_clinical_summary_generation_and_grounding(auth_tokens):
    """Test generating a grounded clinical summary with vitals, complaint, and citations."""
    headers = {"Authorization": f"Bearer {auth_tokens['doctor']}"}

    # 1. Register a patient with unique contact
    pat_payload = {
        "full_name": "Ramesh Gupta",
        "contact": "9811223344",
        "age": 58,
        "gender": "Male",
    }
    p_resp = client.post("/api/v1/patients", json=pat_payload, headers=headers)
    assert p_resp.status_code == 201
    patient_id = p_resp.json()["patient_code"]

    # 2. Add an encounter with acute symptoms and vitals
    enc_payload = {
        "patient_code": patient_id,
        "department": "Cardiology",
        "chief_complaint": "Acute substernal chest pain radiating to left jaw",
        "symptoms": ["chest pain", "shortness of breath", "diaphoresis"],
        "vitals": {
            "systolic_bp": 178.0,
            "diastolic_bp": 104.0,
            "heart_rate": 118.0,
            "respiratory_rate": 24.0,
            "temperature": 98.8,
            "spo2": 93.0,
        },
    }
    e_resp = client.post("/api/v1/encounters", json=enc_payload, headers=headers)
    assert e_resp.status_code == 201
    encounter_id = e_resp.json()["encounter_id"]

    # 3. Generate summary
    sum_resp = client.post(f"/api/v1/summaries/encounter/{encounter_id}", headers=headers)
    assert sum_resp.status_code == 201
    data = sum_resp.json()

    assert data["encounter_id"] == encounter_id
    assert "chest pain" in data["chief_complaint_synopsis"].lower()
    assert "93" in data["vitals_objective_assessment"] or "spo2" in data["vitals_objective_assessment"].lower()
    assert len(data["differential_considerations"]) > 0
    assert len(data["grounded_citations"]) > 0
    assert data["doctor_review_status"] == "PENDING_REVIEW"

    # Verify at least one differential touches coronary syndrome
    diff_names = [d["condition_name"].lower() for d in data["differential_considerations"]]
    assert any("coronary" in d or "cardiac" in d or "angina" in d for d in diff_names)

    # 4. Fetch the summary via GET
    get_resp = client.get(f"/api/v1/summaries/encounter/{encounter_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == data["id"]

    # 5. Doctor review checkpoint (Acceptance)
    review_payload = {
        "status": "ACCEPTED",
        "doctor_notes": "Agreed with differential. Immediate ECG and cardiac enzymes ordered.",
    }
    rev_resp = client.patch(f"/api/v1/summaries/encounter/{encounter_id}/review", json=review_payload, headers=headers)
    assert rev_resp.status_code == 200
    rev_data = rev_resp.json()
    assert rev_data["doctor_review_status"] == "ACCEPTED"
    assert "Immediate ECG" in rev_data["doctor_notes"]
    assert rev_data["reviewed_by_doctor_id"] is not None


def test_receptionist_cannot_review_summary(auth_tokens):
    """Verify RBAC: non-doctors are prohibited from approving/editing clinical summaries."""
    doc_headers = {"Authorization": f"Bearer {auth_tokens['doctor']}"}
    rec_headers = {"Authorization": f"Bearer {auth_tokens['receptionist']}"}

    # Register patient & encounter
    p_resp = client.post("/api/v1/patients", json={"full_name": "Sita Devi", "contact": "9811998877", "age": 42, "gender": "Female"}, headers=rec_headers)
    assert p_resp.status_code == 201
    patient_id = p_resp.json()["patient_code"]

    e_resp = client.post("/api/v1/encounters", json={"patient_code": patient_id, "department": "General Medicine", "chief_complaint": "Persistent headache"}, headers=rec_headers)
    assert e_resp.status_code == 201
    encounter_id = e_resp.json()["encounter_id"]

    # Generate summary (accessible by staff)
    sum_resp = client.post(f"/api/v1/summaries/encounter/{encounter_id}", headers=rec_headers)
    assert sum_resp.status_code == 201

    # Receptionist attempts to approve clinical review
    rev_resp = client.patch(
        f"/api/v1/summaries/encounter/{encounter_id}/review",
        json={"status": "ACCEPTED", "doctor_notes": "Attempted unauthorized review"},
        headers=rec_headers,
    )
    # Must fail with 403 Forbidden
    assert rev_resp.status_code == 403
