"""Automated Consistency Tests for OPD Queue, Emergency Safety Screening, and Triage Priority.

Covers:
- Critical hypoxia (SpO2 = 60% and <90%)
- Normal SpO2 (SpO2 = 98%)
- Normal SpO2 with high-acuity presenting symptoms
- Missing vitals resilience
- Consistent queue counts across /queue, /queue/summary, /announcements/board, and /stats/daily
- New and returning patient registration lifecycle
- ML inference pre-screening emergency override
"""
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.auth_service import seed_default_accounts
from app.services.triage_service import calculate_triage_priority
from app.schemas.triage import TriageInput

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_accounts():
    seed_default_accounts()


def get_doctor_token() -> str:
    resp = client.post("/api/v1/auth/login", json={"email": "doctor@medqueue.org", "password": "doctor123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_critical_hypoxia_emergency_screening_60_percent():
    """Verify that an SpO2 reading of 60% is immediately escalated and flagged for probe recheck."""
    phone = f"9{uuid.uuid4().int % 1000000000:09d}"
    p_resp = client.post("/api/v1/patients", json={
        "full_name": "Hypoxic Patient Test",
        "age": 62,
        "gender": "Male",
        "contact": phone,
    })
    assert p_resp.status_code == 201
    p_code = p_resp.json()["patient_code"]

    # Intake with SpO2 = 60%
    e_resp = client.post("/api/v1/encounters", json={
        "patient_code": p_code,
        "department": "Emergency OPD",
        "chief_complaint": "Acute respiratory distress and dizziness",
        "symptoms": ["Shortness of Breath"],
        "vitals": {
            "spo2": 60.0,
            "heart_rate": 110,
            "systolic_bp": 115,
            "diastolic_bp": 75,
        },
    })
    assert e_resp.status_code == 201
    enc_data = e_resp.json()

    # 1. Immediate escalation triggered
    assert enc_data["is_emergency"] is True
    assert enc_data["escalation_level"] == "IMMEDIATE_ESCALATION"
    assert enc_data["status"] == "ESCALATED_EMERGENCY"

    # 2. Reasons must mention hypoxia and probe verification
    reasons_str = " ".join(enc_data["escalation_reasons"])
    assert "CRITICAL HYPOXIA" in reasons_str
    assert "SENSOR VERIFICATION" in reasons_str or "artifact" in reasons_str.lower() or "probe" in reasons_str.lower()

    # 3. Action guidance must require probe recheck without delaying supportive care
    assert "recheck" in enc_data["action_required"].lower()
    assert "delaying" in enc_data["action_required"].lower()

    # 4. Enqueue into active queue
    q_resp = client.post("/api/v1/queue", json={
        "patient_code": p_code,
        "encounter_id": enc_data["encounter_id"],
        "initial_priority": 1,
    })
    assert q_resp.status_code == 201
    q_data = q_resp.json()
    assert q_data["is_emergency"] is True
    assert q_data["recommended_priority"] == 1
    assert q_data["clinician_approved_priority"] == 1


def test_critical_hypoxia_ml_inference_pre_screening_override():
    """Verify that ML inference runs emergency screening before ML prediction and overrides low acuity."""
    payload = {
        "age": 55,
        "sex": "M",
        "arrival_mode": "walk-in",
        "chief_complaint_system": "respiratory",
        "mental_status_triage": "alert",
        "systolic_bp": 120.0,
        "diastolic_bp": 80.0,
        "heart_rate": 75.0,
        "respiratory_rate": 18.0,
        "temperature_c": 36.8,
        "spo2": 60.0,  # Critical hypoxia (60%)
        "gcs_total": 15.0,
        "pain_score": 1.0,
        "model_type": "model_b_random_forest",
    }
    resp = client.post("/api/v1/models/predict", json=payload)
    assert resp.status_code == 200
    res = resp.json()

    # Even if model would predict routine acuity, pre-screening safety layer overrides it:
    assert res["is_emergency"] is True
    assert res["urgency_tier"] == "HIGH"
    assert res["predicted_acuity"] == 1

    factors_str = " ".join(res["contributing_factors"])
    assert "EMERGENCY SAFETY OVERRIDE" in factors_str
    assert "CRITICAL HYPOXIA" in factors_str
    assert "CLINICAL GOVERNANCE" in factors_str


def test_normal_spo2_stable_case():
    """Verify normal SpO2 (98%) in a routine patient is not flagged as emergency."""
    payload = {
        "age": 30,
        "sex": "F",
        "arrival_mode": "walk-in",
        "chief_complaint_system": "general",
        "mental_status_triage": "alert",
        "systolic_bp": 118.0,
        "diastolic_bp": 78.0,
        "heart_rate": 72.0,
        "respiratory_rate": 16.0,
        "temperature_c": 37.0,
        "spo2": 98.0,
        "gcs_total": 15.0,
        "pain_score": 1.0,
        "model_type": "model_b_random_forest",
    }
    resp = client.post("/api/v1/models/predict", json=payload)
    assert resp.status_code == 200
    res = resp.json()
    assert res["is_emergency"] is False
    assert res["urgency_tier"] in ["LOW", "MEDIUM"]


def test_normal_spo2_with_red_flag_symptom():
    """Verify patient with SpO2 = 98% presenting with acute chest pain is properly escalated."""
    phone = f"9{uuid.uuid4().int % 1000000000:09d}"
    p_resp = client.post("/api/v1/patients", json={
        "full_name": "Chest Pain Patient",
        "age": 58,
        "gender": "Male",
        "contact": phone,
    })
    p_code = p_resp.json()["patient_code"]

    e_resp = client.post("/api/v1/encounters", json={
        "patient_code": p_code,
        "chief_complaint": "Crushing retrosternal chest pain radiating to left arm",
        "symptoms": ["Chest Pain"],
        "vitals": {
            "spo2": 98.0,  # Normal SpO2
            "heart_rate": 92,
            "systolic_bp": 140,
            "diastolic_bp": 90,
        },
    })
    assert e_resp.status_code == 201
    enc_data = e_resp.json()
    # Must trigger immediate emergency escalation due to red-flag symptom
    assert enc_data["is_emergency"] is True
    assert enc_data["escalation_level"] == "IMMEDIATE_ESCALATION"
    assert any("RED-FLAG" in r for r in enc_data["escalation_reasons"])


def test_missing_vitals_handling():
    """Verify that omitted vitals are explicitly recorded as missing and not silently defaulted."""
    phone = f"9{uuid.uuid4().int % 1000000000:09d}"
    p_resp = client.post("/api/v1/patients", json={
        "full_name": "Missing Vitals Patient",
        "age": 40,
        "gender": "Female",
        "contact": phone,
    })
    p_code = p_resp.json()["patient_code"]

    e_resp = client.post("/api/v1/encounters", json={
        "patient_code": p_code,
        "chief_complaint": "Dermatological rash",
        "symptoms": ["Allergic Reaction"],
        "vitals": {
            # Omitting spo2, systolic_bp, diastolic_bp, heart_rate, temperature
        },
    })
    assert e_resp.status_code == 201
    data = e_resp.json()
    indicators = data["missingness_indicators"]
    assert indicators["spo2_missing"] is True
    assert indicators["systolic_bp_missing"] is True
    assert indicators["heart_rate_missing"] is True


def test_queue_count_consistency_across_endpoints():
    """Verify that /queue, /queue/summary, /announcements/board, and /stats/daily report identical counts."""
    phone_new = f"9{uuid.uuid4().int % 1000000000:09d}"
    phone_ret = f"9{uuid.uuid4().int % 1000000000:09d}"

    # 1. Register Patient 1 (New)
    p1 = client.post("/api/v1/patients", json={"full_name": "Queue Patient 1", "age": 30, "gender": "Female", "contact": phone_new}).json()["patient_code"]
    e1 = client.post("/api/v1/encounters", json={"patient_code": p1, "chief_complaint": "General visit", "vitals": {"spo2": 98.0}}).json()["encounter_id"]
    client.post("/api/v1/queue", json={"patient_code": p1, "encounter_id": e1, "initial_priority": 3})

    # 2. Register Patient 2 (Returning)
    p2 = client.post("/api/v1/patients", json={"full_name": "Queue Patient 2", "age": 45, "gender": "Male", "contact": phone_ret}).json()["patient_code"]
    # Re-register with same phone -> identity matching
    p2_match = client.post("/api/v1/patients", json={"full_name": "Queue Patient 2", "age": 45, "gender": "Male", "contact": phone_ret}).json()["patient_code"]
    assert p2 == p2_match

    e2 = client.post("/api/v1/encounters", json={"patient_code": p2, "visit_type": "RETURNING", "chief_complaint": "Returning visit", "vitals": {"spo2": 97.0}}).json()["encounter_id"]
    client.post("/api/v1/queue", json={"patient_code": p2, "encounter_id": e2, "initial_priority": 3})

    # 3. Query all endpoints
    active_queue = client.get("/api/v1/queue").json()
    waiting_in_queue = sum(1 for q in active_queue if q["queue_status"] == "WAITING")

    summary_resp = client.get("/api/v1/queue/summary").json()
    waiting_in_summary = summary_resp["total_waiting"]

    board_resp = client.get("/api/v1/announcements/board").json()
    waiting_in_board = board_resp["total_waiting"]

    stats_resp = client.get("/api/v1/stats/daily").json()
    waiting_in_stats = stats_resp["waiting_count"]

    # All waiting counts must be strictly identical
    assert waiting_in_queue == waiting_in_summary
    assert waiting_in_summary == waiting_in_board
    assert waiting_in_board == waiting_in_stats


def test_triage_service_priority_calculation():
    """Verify triage_service priority and severity calculations."""
    # Critical hypoxia case: SpO2 = 60%
    hypoxic_input = TriageInput(
        age=45,
        spo2=60.0,
        heart_rate=75,
        blood_pressure="120/80",
        temperature=98.6,
        symptoms=["cough"],
    )
    res_hypoxic = calculate_triage_priority(hypoxic_input)
    assert res_hypoxic.severity == "HIGH"
    assert res_hypoxic.is_emergency is True
    assert res_hypoxic.priority_score >= 90

    # Normal stable case: SpO2 = 98%
    stable_input = TriageInput(
        age=30,
        spo2=98.0,
        heart_rate=72,
        blood_pressure="120/80",
        temperature=98.6,
        symptoms=["mild fatigue"],
    )
    res_stable = calculate_triage_priority(stable_input)
    assert res_stable.severity == "LOW"
    assert res_stable.is_emergency is False
    assert res_stable.priority_score < 45
