"""Automated Integration & Safety Tests for Patients, Encounters, and Emergency Screening."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_register_new_patient():
    """Test registering a brand new patient profile."""
    payload = {
        "full_name": "Ravi Kumar",
        "age": 45,
        "gender": "Male",
        "contact": "9876543210",
        "emergency_contact": "9876543211",
        "blood_group": "B+",
        "preferred_language": "Telugu",
        "accessibility_needs": "None",
    }
    response = client.post("/api/v1/patients", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["full_name"] == "Ravi Kumar"
    assert data["patient_code"].startswith("PAT-")
    assert data["total_encounters"] == 0
    assert data["preferred_language"] == "Telugu"


def test_returning_patient_identity_matching():
    """Test that registering with an existing phone number returns the existing record."""
    # First registration
    payload1 = {
        "full_name": "Sunita Devi",
        "age": 52,
        "gender": "Female",
        "contact": "9123456789",
    }
    resp1 = client.post("/api/v1/patients", json=payload1)
    assert resp1.status_code == 201
    code1 = resp1.json()["patient_code"]

    # Second registration attempt with identical phone number
    payload2 = {
        "full_name": "Sunita Devi Updated",
        "age": 52,
        "gender": "Female",
        "contact": "9123456789",
    }
    resp2 = client.post("/api/v1/patients", json=payload2)
    assert resp2.status_code == 201
    code2 = resp2.json()["patient_code"]
    # Verified identity matching: prevents duplicate patient code creation
    assert code1 == code2


def test_create_standard_encounter():
    """Test creating an encounter for a stable outpatient."""
    # Register patient
    p_resp = client.post("/api/v1/patients", json={
        "full_name": "Aarav Sharma",
        "age": 30,
        "gender": "Male",
        "contact": "9988776655",
    })
    p_code = p_resp.json()["patient_code"]

    enc_payload = {
        "patient_code": p_code,
        "department": "General Medicine",
        "visit_type": "NEW",
        "chief_complaint": "Mild seasonal dry cough for 3 days",
        "complaint_category": "Respiratory",
        "symptom_duration": "3 days",
        "symptoms": ["Cough", "Mild Headache"],
        "vitals": {
            "temperature": 98.6,
            "heart_rate": 72,
            "respiratory_rate": 16,
            "systolic_bp": 120,
            "diastolic_bp": 80,
            "spo2": 99.0,
            "blood_sugar": 105.0,
            "pain_score": 1,
        },
        "measurement_source": "TRIAGE_NURSE",
    }

    e_resp = client.post("/api/v1/encounters", json=enc_payload)
    assert e_resp.status_code == 201
    data = e_resp.json()
    assert data["encounter_id"].startswith("ENC-")
    assert data["is_emergency"] is False
    assert data["escalation_level"] == "STANDARD"
    assert data["status"] == "WAITING"
    assert data["missingness_indicators"]["spo2_missing"] is False


def test_create_emergency_encounter_hypoxia():
    """Test that critical SpO2 (<90%) triggers immediate emergency escalation."""
    p_resp = client.post("/api/v1/patients", json={
        "full_name": "Lakshmi Narayana",
        "age": 68,
        "gender": "Male",
        "contact": "9555444333",
    })
    p_code = p_resp.json()["patient_code"]

    enc_payload = {
        "patient_code": p_code,
        "department": "Pulmonology",
        "visit_type": "RETURNING",
        "chief_complaint": "Severe breathlessness, unable to speak in full sentences",
        "symptoms": ["Difficulty Breathing", "Fatigue"],
        "vitals": {
            "spo2": 86.0,  # Critical hypoxia threshold < 90%
            "heart_rate": 118,
            "respiratory_rate": 30,
            "systolic_bp": 135,
            "diastolic_bp": 85,
        },
    }

    e_resp = client.post("/api/v1/encounters", json=enc_payload)
    assert e_resp.status_code == 201
    data = e_resp.json()
    assert data["is_emergency"] is True
    assert data["escalation_level"] == "IMMEDIATE_ESCALATION"
    assert data["status"] == "ESCALATED_EMERGENCY"
    assert any("CRITICAL HYPOXIA" in r for r in data["escalation_reasons"])
    assert "IMMEDIATE CLINICAL ESCALATION REQUIRED" in data["action_required"]


def test_create_emergency_encounter_hypertensive_crisis():
    """Test that SBP >= 180 triggers hypertensive crisis emergency alert."""
    p_resp = client.post("/api/v1/patients", json={
        "full_name": "Kalyani Rao",
        "age": 59,
        "gender": "Female",
        "contact": "9444333222",
    })
    p_code = p_resp.json()["patient_code"]

    enc_payload = {
        "patient_code": p_code,
        "department": "Cardiology",
        "visit_type": "NEW",
        "chief_complaint": "Pounding occipital headache and blurred vision",
        "symptoms": ["Severe Headache", "High Blood Pressure"],
        "vitals": {
            "systolic_bp": 195,  # Hypertensive crisis >= 180
            "diastolic_bp": 115,  # >= 110
            "heart_rate": 88,
            "spo2": 97.0,
        },
    }

    e_resp = client.post("/api/v1/encounters", json=enc_payload)
    assert e_resp.status_code == 201
    data = e_resp.json()
    assert data["is_emergency"] is True
    assert data["escalation_level"] == "IMMEDIATE_ESCALATION"
    assert any("HYPERTENSIVE CRISIS" in r for r in data["escalation_reasons"])


def test_explicit_missingness_representation():
    """Test that missing vitals are explicitly recorded as missing and not fabricated."""
    p_resp = client.post("/api/v1/patients", json={
        "full_name": "Meera Patel",
        "age": 25,
        "gender": "Female",
        "contact": "9333222111",
    })
    p_code = p_resp.json()["patient_code"]

    # Intake where blood pressure and respiratory rate could not be obtained
    enc_payload = {
        "patient_code": p_code,
        "chief_complaint": "Follow-up rash on forearm",
        "symptoms": ["Allergic Reaction"],
        "vitals": {
            "temperature": 98.4,
            "heart_rate": 74,
            "spo2": 99.0,
            # systolic_bp, diastolic_bp, respiratory_rate are omitted
        },
    }

    e_resp = client.post("/api/v1/encounters", json=enc_payload)
    assert e_resp.status_code == 201
    data = e_resp.json()
    indicators = data["missingness_indicators"]
    assert indicators["systolic_bp_missing"] is True
    assert indicators["diastolic_bp_missing"] is True
    assert indicators["respiratory_rate_missing"] is True
    assert indicators["temperature_missing"] is False
    assert indicators["heart_rate_missing"] is False
    # Verify vitals dict has None rather than fake numbers
    assert data["vitals"]["systolic_bp"] is None


def test_get_patient_encounters_list():
    """Test retrieving chronological encounters for a patient."""
    p_resp = client.post("/api/v1/patients", json={
        "full_name": "Venkat Raman",
        "age": 42,
        "gender": "Male",
        "contact": "9222111000",
    })
    p_code = p_resp.json()["patient_code"]

    client.post("/api/v1/encounters", json={
        "patient_code": p_code,
        "chief_complaint": "Visit 1 fever",
        "symptoms": ["Fever"],
    })
    client.post("/api/v1/encounters", json={
        "patient_code": p_code,
        "chief_complaint": "Visit 2 follow up",
        "symptoms": ["Fatigue"],
    })

    list_resp = client.get(f"/api/v1/patients/{p_code}/encounters")
    assert list_resp.status_code == 200
    encounters = list_resp.json()
    assert len(encounters) == 2
    assert encounters[0]["patient_code"] == p_code


def test_search_patients():
    """Test searching patient directory by name or phone."""
    client.post("/api/v1/patients", json={
        "full_name": "UniqueSearchableName",
        "age": 35,
        "gender": "Female",
        "contact": "9111000999",
    })

    search_resp = client.get("/api/v1/patients?query=UniqueSearchable")
    assert search_resp.status_code == 200
    results = search_resp.json()
    assert len(results) >= 1
    assert any(r["full_name"] == "UniqueSearchableName" for r in results)
