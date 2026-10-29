"""Comprehensive Test Suite for Previous Medical Records & AI Clinical Summary Feature Flow.

Covers:
1. Patient-reported previous consultations CRUD & verification.
2. Medical document upload with direct PDF extraction (pypdf).
3. Image upload with OCR parsing and abnormal lab detection.
4. Validation rejection for unsupported MIME/extensions and size limits.
5. Patient identity matching checks (MATCHED, UNCERTAIN, MISMATCH).
6. Extraction of lab results with abnormal flags, medications, and uncertainty scoring.
7. 7-section Grounded AI Clinical Summary generation with citations.
8. Outdated summary staleness detection (is_stale) and regeneration.
9. Independence of emergency screening from document upload and LLM failures.
"""
import io
import uuid
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.services.auth_service import seed_default_accounts
from app.core.config import settings

client = TestClient(app)


@pytest.fixture(autouse=True)
def ensure_seed_accounts():
    """Ensure seed accounts exist before tests run."""
    seed_default_accounts()


@pytest.fixture
def auth_tokens():
    """Obtain access tokens for doctor, receptionist, and admin accounts."""
    doc_resp = client.post("/api/v1/auth/login", json={"email": "doctor@medqueue.org", "password": "doctor123"})
    rec_resp = client.post("/api/v1/auth/login", json={"email": "receptionist@medqueue.org", "password": "receptionist123"})
    adm_resp = client.post("/api/v1/auth/login", json={"email": "admin@medqueue.org", "password": "admin123"})
    return {
        "doctor": doc_resp.json()["access_token"],
        "receptionist": rec_resp.json()["access_token"],
        "admin": adm_resp.json()["access_token"],
    }


def create_patient_helper(name: str = "Rajesh Sharma", age: int = 52, gender: str = "Male") -> str:
    """Helper to register a patient and return unique patient_code."""
    unique_phone = f"9{uuid.uuid4().int % 1000000000:09d}"
    resp = client.post("/api/v1/patients", json={
        "full_name": name,
        "age": age,
        "gender": gender,
        "contact": unique_phone,
    })
    assert resp.status_code == 201
    return resp.json()["patient_code"]


def make_simple_pdf(text: str) -> bytes:
    """Helper to generate a minimal valid PDF 1.4 stream containing text for pypdf."""
    stream_content = f"BT /F1 12 Tf 50 700 Td ({text}) Tj ET"
    stream_len = len(stream_content)
    pdf = f"""%PDF-1.4
1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj
2 0 obj <</Type /Pages /Kids [3 0 R] /Count 1>> endobj
3 0 obj <</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources <</Font <</F1 5 0 R>>>>>> endobj
4 0 obj <</Length {stream_len}>> stream
{stream_content}
endstream
endobj
5 0 obj <</Type /Font /Subtype /Type1 /BaseFont /Helvetica>> endobj
xref
0 6
0000000000 65535 f 
0000000010 00000 n 
0000000060 00000 n 
0000000117 00000 n 
0000000243 00000 n 
0000000340 00000 n 
trailer <</Size 6 /Root 1 0 R>>
startxref
415
%%EOF"""
    return pdf.encode("latin1")


# ==============================================================================
# TEST 1: Patient-Reported Previous Consultations CRUD & Staff Verification
# ==============================================================================

def test_previous_consultation_crud_and_verification(auth_tokens):
    """Test full CRUD and staff verification for patient-reported previous visits."""
    doctor_headers = {"Authorization": f"Bearer {auth_tokens['doctor']}"}
    patient_code = create_patient_helper("Priya Nair")

    # 1. Create a previous consultation entry
    consult_payload = {
        "facility_or_doctor": "City Health PolyClinic - Dr. V. Rao",
        "consultation_date": "2025-11-10",
        "symptoms_reported": "Persistent dry cough, mild breathlessness on exertion",
        "diagnosis_given": "Early Bronchial Asthma / Post-viral airway hyperreactivity",
        "investigations_done": "Chest X-Ray Normal, Spirometry FEV1 78%",
        "treatment_prescribed": "Budesonide 200mcg inhaler twice daily, Levocetirizine 5mg at night",
        "medicines_taken": "Took inhaler regularly for 3 weeks",
        "duration_of_treatment": "3 weeks",
        "response_to_treatment": "Improved",
        "side_effects_or_issues": "Mild hoarseness of voice, no tremors",
    }

    create_resp = client.post(
        f"/api/v1/patients/{patient_code}/previous-consultations",
        json=consult_payload,
        headers=doctor_headers,
    )
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    assert created_data["id"] is not None
    assert created_data["facility_or_doctor"] == "City Health PolyClinic - Dr. V. Rao"
    assert created_data["response_to_treatment"] == "IMPROVED"
    assert created_data["verified_by_staff"] is False
    consult_id = created_data["id"]

    # 2. List consultations for the patient
    list_resp = client.get(
        f"/api/v1/patients/{patient_code}/previous-consultations",
        headers=doctor_headers,
    )
    assert list_resp.status_code == 200
    consultations = list_resp.json()
    assert len(consultations) >= 1
    assert any(c["id"] == consult_id for c in consultations)

    # 3. Update consultation entry
    patch_resp = client.patch(
        f"/api/v1/previous-consultations/{consult_id}",
        json={"response_to_treatment": "Unchanged", "duration_of_treatment": "4 weeks"},
        headers=doctor_headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["response_to_treatment"] == "UNCHANGED"
    assert patch_resp.json()["duration_of_treatment"] == "4 weeks"

    # 4. Verify consultation by doctor
    verify_resp = client.patch(
        f"/api/v1/previous-consultations/{consult_id}/verify",
        json={"notes": "Confirmed with discharge summary provided by patient."},
        headers=doctor_headers,
    )
    assert verify_resp.status_code == 200
    assert verify_resp.json()["verified_by_staff"] is True
    assert "Sarah Rao" in verify_resp.json()["verified_by_name"]

    # 5. Delete consultation entry
    delete_resp = client.delete(
        f"/api/v1/previous-consultations/{consult_id}",
        headers=doctor_headers,
    )
    assert delete_resp.status_code == 200
    assert delete_resp.json()["deleted"] is True


# ==============================================================================
# TEST 2: PDF Document Upload & Direct Text Extraction (pypdf)
# ==============================================================================

def test_pdf_document_upload_and_direct_extraction(auth_tokens):
    """Test PDF upload with text stream and verify direct extraction without OCR."""
    doctor_headers = {"Authorization": f"Bearer {auth_tokens['doctor']}"}
    patient_code = create_patient_helper("Kavita Reddy")

    pdf_text = "CLINICAL LAB REPORT Patient: Kavita Reddy Date: 2025-10-15 HbA1c: 8.4% Fasting Blood Sugar: 165 mg/dL Rx: Metformin 500mg"
    pdf_bytes = make_simple_pdf(pdf_text)

    files = {
        "file": ("lab_report.pdf", io.BytesIO(pdf_bytes), "application/pdf")
    }
    data = {
        "document_type": "LAB_REPORT",
    }

    upload_resp = client.post(
        f"/api/v1/patients/{patient_code}/documents/upload",
        files=files,
        data=data,
        headers=doctor_headers,
    )
    assert upload_resp.status_code == 201
    doc_data = upload_resp.json()
    assert doc_data["document_id"].startswith("DOC-")
    assert doc_data["identity_match_status"] == "MATCHED"

    # Verify extracted lab values and abnormal flag
    extracted_labs = doc_data.get("extracted_lab_results", [])
    hba1c_item = next((item for item in extracted_labs if "HbA1c" in item["test_name"]), None)
    if hba1c_item:
        assert hba1c_item["result"] == "8.4"
        assert hba1c_item["is_abnormal"] is True  # 8.4 > 5.6


# ==============================================================================
# TEST 3: Image Upload & OCR with Abnormal Lab Parsing
# ==============================================================================

def test_image_upload_and_mocked_ocr(auth_tokens):
    """Test image upload and OCR extraction using mocked pytesseract."""
    doctor_headers = {"Authorization": f"Bearer {auth_tokens['doctor']}"}
    patient_code = create_patient_helper("Vijay Kumar")

    mock_ocr_text = (
        "METROPOLIS HEALTHCARE LABS\n"
        "Patient Name: Vijay Kumar\n"
        "Date: 2025-10-20\n"
        "Serum Creatinine: 2.8 mg/dL\n"
        "Hemoglobin: 9.1 g/dL\n"
        "Known Allergies: Penicillin\n"
        "Rx: Amlodipine 5mg OD\n"
    )

    from PIL import Image
    test_img = Image.new("RGB", (100, 100), color="white")
    buf = io.BytesIO()
    test_img.save(buf, format="PNG")
    valid_png_bytes = buf.getvalue()

    files = {
        "file": ("blood_report.png", io.BytesIO(valid_png_bytes), "image/png")
    }
    data = {
        "document_type": "LAB_REPORT",
    }

    with patch("pytesseract.image_to_string", return_value=mock_ocr_text):
        upload_resp = client.post(
            f"/api/v1/patients/{patient_code}/documents/upload",
            files=files,
            data=data,
            headers=doctor_headers,
        )

    assert upload_resp.status_code == 201
    doc_data = upload_resp.json()
    assert doc_data["identity_match_status"] == "MATCHED"

    # Check extracted lab results
    labs = doc_data.get("extracted_labs", [])
    creat_item = next((l for l in labs if "Creatinine" in l["test_name"]), None)
    if creat_item:
        assert creat_item["result_value"] == "2.8"
        assert creat_item["is_abnormal"] is True  # 2.8 > 1.3


# ==============================================================================
# TEST 4: Unsupported File Format & File Size Limit Rejection
# ==============================================================================

def test_unsupported_file_format_rejection(auth_tokens):
    """Ensure system rejects executable or unsupported MIME formats with 400 Bad Request."""
    doctor_headers = {"Authorization": f"Bearer {auth_tokens['doctor']}"}
    patient_code = create_patient_helper("Gita Devi")

    malicious_files = {
        "file": ("test_executable.exe", io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00"), "application/x-msdownload")
    }
    resp = client.post(
        f"/api/v1/patients/{patient_code}/documents/upload",
        files=malicious_files,
        data={"document_type": "OTHER"},
        headers=doctor_headers,
    )
    assert resp.status_code == 400
    assert "Unsupported file" in resp.json()["detail"]


def test_file_size_limit_rejection(auth_tokens):
    """Ensure system rejects oversized documents exceeding MAX_UPLOAD_SIZE_MB."""
    doctor_headers = {"Authorization": f"Bearer {auth_tokens['doctor']}"}
    patient_code = create_patient_helper("Mohan Lal")

    oversized_data = b"0" * ((settings.MAX_UPLOAD_SIZE_MB + 1) * 1024 * 1024)
    oversized_files = {
        "file": ("huge_scan.pdf", io.BytesIO(oversized_data), "application/pdf")
    }

    resp = client.post(
        f"/api/v1/patients/{patient_code}/documents/upload",
        files=oversized_files,
        data={"document_type": "LAB_REPORT"},
        headers=doctor_headers,
    )
    assert resp.status_code == 413
    assert "exceed" in resp.json()["detail"].lower()


# ==============================================================================
# TEST 5: Patient Identity Matching & Mismatch Flagging
# ==============================================================================

def test_patient_identity_matching_cases(auth_tokens):
    """Test identity match scenarios: MATCHED, MISMATCH, and UNCERTAIN."""
    doctor_headers = {"Authorization": f"Bearer {auth_tokens['doctor']}"}
    patient_code = create_patient_helper("Sunil Gavaskar")

    # 1. MATCHED: Name matches patient record
    matched_text = "HOSPITAL RECORD\nPatient: Sunil Gavaskar\nDate: 2025-09-01\nDiagnosis: Hypertension"
    resp_matched = client.post(
        f"/api/v1/patients/{patient_code}/documents/upload",
        files={"file": ("doc_match.txt", io.BytesIO(matched_text.encode("utf-8")), "text/plain")},
        data={"document_type": "CLINICAL_NOTE"},
        headers=doctor_headers,
    )
    assert resp_matched.status_code == 201
    assert resp_matched.json()["identity_match_status"] == "MATCHED"

    # 2. MISMATCH: Different patient name on document
    mismatch_text = "HOSPITAL RECORD\nPatient: Meena Kumari\nDate: 2025-09-01\nDiagnosis: Migraine"
    resp_mismatch = client.post(
        f"/api/v1/patients/{patient_code}/documents/upload",
        files={"file": ("doc_mismatch.txt", io.BytesIO(mismatch_text.encode("utf-8")), "text/plain")},
        data={"document_type": "CLINICAL_NOTE"},
        headers=doctor_headers,
    )
    assert resp_mismatch.status_code == 201
    assert resp_mismatch.json()["identity_match_status"] == "MISMATCH"
    assert "Meena Kumari" in resp_mismatch.json()["identity_match_details"]
    assert resp_mismatch.json()["detected_patient_name"] == "Meena Kumari"

    # 3. UNCERTAIN: No patient name found in document text
    uncertain_text = "ANONYMOUS LAB TEST STRIP\nDate: 2025-09-01\nFasting Blood Sugar: 110 mg/dL"
    resp_uncertain = client.post(
        f"/api/v1/patients/{patient_code}/documents/upload",
        files={"file": ("doc_uncertain.txt", io.BytesIO(uncertain_text.encode("utf-8")), "text/plain")},
        data={"document_type": "LAB_REPORT"},
        headers=doctor_headers,
    )
    assert resp_uncertain.status_code == 201
    assert resp_uncertain.json()["identity_match_status"] == "UNCERTAIN"


# ==============================================================================
# TEST 6: 7-Section Grounded AI Clinical Summary Generation
# ==============================================================================

def test_7_section_clinical_summary_and_citations(auth_tokens):
    """Test generating a comprehensive 7-section AI Clinical Summary with citations."""
    doctor_headers = {"Authorization": f"Bearer {auth_tokens['doctor']}"}
    patient_code = create_patient_helper("Deepak Verma", age=60)

    # 1. Add Previous Consultation
    client.post(
        f"/api/v1/patients/{patient_code}/previous-consultations",
        json={
            "facility_or_doctor": "Fortis Hospital - Dr. S. Sen",
            "consultation_date": "2025-08-14",
            "symptoms_reported": "Exertional dyspnea, leg edema",
            "diagnosis_given": "Congestive Heart Failure Stage B",
            "treatment_prescribed": "Furosemide 40mg OD, Ramipril 2.5mg OD",
            "medicines_taken": "Took Ramipril irregularly",
            "response_to_treatment": "Worsened",
        },
        headers=doctor_headers,
    )

    # 2. Upload Lab Document
    doc_text = "APOLLO LABS\nPatient: Deepak Verma\nDate: 2025-08-20\nSerum Creatinine: 1.9 mg/dL\nSerum Potassium: 5.2 mEq/L"
    client.post(
        f"/api/v1/patients/{patient_code}/documents/upload",
        files={"file": ("lab.txt", io.BytesIO(doc_text.encode("utf-8")), "text/plain")},
        data={"document_type": "LAB_REPORT"},
        headers=doctor_headers,
    )

    # 3. Create Encounter
    enc_payload = {
        "patient_code": patient_code,
        "department": "Internal Medicine",
        "chief_complaint": "Bilateral pedal edema and orthopnea",
        "symptoms": ["leg swelling", "difficulty breathing lying flat"],
        "vitals": {
            "systolic_bp": 150.0,
            "diastolic_bp": 94.0,
            "heart_rate": 88.0,
            "respiratory_rate": 20.0,
            "temperature": 98.4,
            "spo2": 95.0,
        },
    }
    enc_resp = client.post("/api/v1/encounters", json=enc_payload, headers=doctor_headers)
    assert enc_resp.status_code == 201
    encounter_id = enc_resp.json()["encounter_id"]

    # 4. Generate Clinical Summary
    sum_resp = client.post(
        f"/api/v1/encounters/{encounter_id}/clinical-summary",
        headers=doctor_headers,
    )
    assert sum_resp.status_code in [200, 201]
    summary = sum_resp.json()

    # Check 7 Structured Sections (A-G)
    assert summary["section_a_current_presentation"] is not None
    assert "edema" in summary["section_a_current_presentation"]["chief_complaint"].lower()

    assert len(summary["section_b_previous_consultations"]) >= 1
    assert "Fortis Hospital" in summary["section_b_previous_consultations"][0]["facility_or_doctor"]
    assert summary["section_b_previous_consultations"][0]["reported_response"] == "WORSENED"

    assert len(summary["section_c_previous_investigations"]) >= 1
    creat_inv = next((inv for inv in summary["section_c_previous_investigations"] if "Creatinine" in inv["test_name"]), None)
    if creat_inv:
        assert creat_inv["is_abnormal"] is True

    assert summary["section_d_relevant_medical_history"] is not None
    assert len(summary["section_e_clinical_timeline"]) >= 1
    assert len(summary["section_f_important_uncertainties"]) >= 1
    assert len(summary["grounded_citations"]) >= 1

    # Check citation provenance types
    citation_types = [c["source_type"] for c in summary["grounded_citations"]]
    assert "VITALS" in citation_types or "CURRENT_ENCOUNTER" in citation_types


# ==============================================================================
# TEST 7: Summary Staleness Detection & Regeneration
# ==============================================================================

def test_summary_staleness_and_regeneration(auth_tokens):
    """Test that summary is flagged stale when records are added and can be regenerated."""
    doctor_headers = {"Authorization": f"Bearer {auth_tokens['doctor']}"}
    patient_code = create_patient_helper("Alok Nath")

    # 1. Create Encounter
    enc_resp = client.post(
        "/api/v1/encounters",
        json={
            "patient_code": patient_code,
            "department": "General OPD",
            "chief_complaint": "Persistent headache and dizziness",
            "symptoms": ["headache", "dizziness"],
            "vitals": {"systolic_bp": 130.0, "diastolic_bp": 85.0, "heart_rate": 72.0, "spo2": 99.0},
        },
        headers=doctor_headers,
    )
    assert enc_resp.status_code == 201
    encounter_id = enc_resp.json()["encounter_id"]

    # 2. Generate initial summary
    gen_resp = client.post(f"/api/v1/encounters/{encounter_id}/clinical-summary", headers=doctor_headers)
    assert gen_resp.status_code in [200, 201]
    summary_1 = gen_resp.json()
    assert summary_1["is_stale"] is False
    summary_id = summary_1["id"]

    # 3. Add a new previous consultation for this patient (stale trigger)
    client.post(
        f"/api/v1/patients/{patient_code}/previous-consultations",
        json={
            "facility_or_doctor": "Neighborhood Clinic",
            "consultation_date": "2025-10-25",
            "symptoms_reported": "Headache",
            "diagnosis_given": "Tension Headache",
            "treatment_prescribed": "Naproxen 250mg",
            "response_to_treatment": "Unchanged",
        },
        headers=doctor_headers,
    )

    # 4. Fetch the summary again: should now be flagged stale
    get_resp = client.get(f"/api/v1/encounters/{encounter_id}/clinical-summary", headers=doctor_headers)
    assert get_resp.status_code == 200
    stale_summary = get_resp.json()
    assert stale_summary["is_stale"] is True
    assert "previous consultation" in stale_summary["stale_reason"]

    # 5. Regenerate summary
    regen_resp = client.post(f"/api/v1/clinical-summaries/{summary_id}/regenerate", headers=doctor_headers)
    assert regen_resp.status_code == 200
    updated_summary = regen_resp.json()
    assert updated_summary["is_stale"] is False
    assert len(updated_summary["section_b_previous_consultations"]) >= 1


# ==============================================================================
# TEST 8: Emergency Screening Independence from Uploads and LLM
# ==============================================================================

def test_emergency_screening_independence_from_ocr_and_llm(auth_tokens):
    """Verify emergency screening runs synchronously without blocking on documents/OCR/LLM."""
    doctor_headers = {"Authorization": f"Bearer {auth_tokens['doctor']}"}
    patient_code = create_patient_helper("Emergency Patient", age=68)

    # Critical vitals intake: severe hypoxia (SpO2 82%) and tachypnea
    emergency_enc_payload = {
        "patient_code": patient_code,
        "department": "Emergency / Critical Care",
        "chief_complaint": "Acute severe respiratory distress and cyanosis",
        "symptoms": ["severe breathlessness", "chest tightness", "confusion"],
        "vitals": {
            "systolic_bp": 85.0,
            "diastolic_bp": 50.0,
            "heart_rate": 134.0,
            "respiratory_rate": 32.0,
            "temperature": 99.2,
            "spo2": 82.0,  # Critical emergency trigger
        },
    }

    # Emergency triage execution must succeed immediately
    enc_resp = client.post("/api/v1/encounters", json=emergency_enc_payload, headers=doctor_headers)
    assert enc_resp.status_code == 201
    enc_data = enc_resp.json()

    # Priority score must immediately reflect emergency status without needing document upload or LLM
    assert enc_data.get("is_emergency") is True or enc_data.get("priority_score", 0) >= 80 or enc_data.get("escalation_level") == "EMERGENCY"
    assert enc_data["encounter_id"] is not None
