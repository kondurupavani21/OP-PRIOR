"""Integration tests for Medical Document Upload, OCR, and Staff Verification."""
import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.auth_service import seed_default_accounts

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_accounts():
    """Ensure seeded accounts exist for testing."""
    seed_default_accounts()


def get_auth_token(email: str = "doctor@medqueue.org", password: str = "doctor123") -> str:
    """Helper to authenticate and return bearer token."""
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def create_test_patient() -> str:
    """Helper to register a patient with a unique phone number and return patient_code."""
    import uuid
    unique_phone = f"9{uuid.uuid4().int % 1000000000:09d}"
    resp = client.post("/api/v1/patients", json={
        "full_name": "Suresh Babu",
        "age": 55,
        "gender": "Male",
        "contact": unique_phone,
    })
    assert resp.status_code == 201
    return resp.json()["patient_code"]


def test_document_upload_and_ocr_extraction():
    """Test document upload and candidate field extraction."""
    patient_code = create_test_patient()

    # Create dummy clinical prescription text file
    doc_content = (
        "APOLLO CLINIC CONSULTATION NOTE\n"
        "Date: 12-08-2025\n"
        "Patient: Suresh Babu\n"
        "Diagnosis: Hypertension, Type 2 Diabetes\n"
        "Rx: Metformin 500mg, Amlodipine 5mg\n"
        "Allergies: Penicillin\n"
    )

    files = {
        "file": ("prescription.txt", io.BytesIO(doc_content.encode("utf-8")), "text/plain")
    }
    data = {
        "document_type": "PRESCRIPTION",
    }

    upload_resp = client.post(f"/api/v1/patients/{patient_code}/documents/upload", files=files, data=data)
    assert upload_resp.status_code == 201
    doc_data = upload_resp.json()
    assert doc_data["document_id"].startswith("DOC-")
    assert doc_data["verification_status"] == "PENDING_REVIEW"
    assert len(doc_data["extracted_fields"]) >= 1

    doc_id = doc_data["document_id"]

    # Verify history is still empty (Unverified OCR cannot auto-promote to clinical history)
    hist_resp = client.get(f"/api/v1/patients/{patient_code}/history")
    assert hist_resp.status_code == 200
    assert len(hist_resp.json()["verified_conditions"]) == 0
    assert hist_resp.json()["has_unverified_documents"] is True

    # Staff Verification Checkpoint
    token = get_auth_token()
    verify_payload = {
        "verification_status": "VERIFIED",
        "reviewer_notes": "Reviewed and confirmed by attending physician.",
        "verified_conditions": ["Hypertension", "Type 2 Diabetes"],
        "verified_medications": ["Metformin", "Amlodipine"],
        "verified_allergies": ["Penicillin"],
    }

    verify_resp = client.patch(
        f"/api/v1/documents/{doc_id}/verify",
        json=verify_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert verify_resp.status_code == 200
    assert verify_resp.json()["verification_status"] == "VERIFIED"

    # Now verify that verified facts are committed to medical_history with provenance
    updated_hist = client.get(f"/api/v1/patients/{patient_code}/history").json()
    assert "Hypertension" in updated_hist["verified_conditions"]
    assert "Type 2 Diabetes" in updated_hist["verified_conditions"]
    assert "Metformin" in updated_hist["active_medications"]
    assert "Penicillin" in updated_hist["known_allergies"]

    # Check source provenance
    provenance_item = updated_hist["history_items"][0]
    assert provenance_item["source_document_id"] == doc_id
    assert provenance_item["verification_status"] == "VERIFIED"


def test_document_rejection_does_not_commit_history():
    """Verify rejected OCR document does NOT commit items to verified medical history."""
    patient_code = create_test_patient()

    doc_content = "Illegible scan with corrupt diagnosis: Asthma"
    files = {
        "file": ("corrupt.txt", io.BytesIO(doc_content.encode("utf-8")), "text/plain")
    }
    upload_resp = client.post(f"/api/v1/patients/{patient_code}/documents/upload", files=files)
    doc_id = upload_resp.json()["document_id"]

    token = get_auth_token()
    verify_resp = client.patch(
        f"/api/v1/documents/{doc_id}/verify",
        json={"verification_status": "REJECTED", "reviewer_notes": "Illegible scan, rejected."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert verify_resp.status_code == 200
    assert verify_resp.json()["verification_status"] == "REJECTED"

    hist = client.get(f"/api/v1/patients/{patient_code}/history").json()
    assert len(hist["verified_conditions"]) == 0
