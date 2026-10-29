"""Test Suite for Machine Learning Triage Inference & Serving."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_models_status_endpoint():
    """Verify GET /api/v1/models/status returns model catalog and metadata."""
    resp = client.get("/api/v1/models/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "is_trained" in data
    assert "available_models" in data
    assert "default_model" in data


def test_triage_predict_standard_case():
    """Verify POST /api/v1/models/predict for standard adult outpatient presentation."""
    payload = {
        "age": 35,
        "sex": "M",
        "arrival_mode": "walk-in",
        "chief_complaint_system": "general",
        "mental_status_triage": "alert",
        "systolic_bp": 120.0,
        "diastolic_bp": 80.0,
        "heart_rate": 72.0,
        "respiratory_rate": 16.0,
        "temperature_c": 36.8,
        "spo2": 98.0,
        "gcs_total": 15.0,
        "pain_score": 2.0,
        "model_type": "model_b_random_forest",
    }
    resp = client.post("/api/v1/models/predict", json=payload)
    assert resp.status_code == 200
    res = resp.json()
    assert 1 <= res["predicted_acuity"] <= 5
    assert res["urgency_tier"] in ["HIGH", "MEDIUM", "LOW"]
    assert 0.0 <= res["confidence"] <= 1.0
    assert len(res["probabilities"]) == 5

    # Verify probability distribution sums to approximately 1.0
    prob_sum = sum(p["probability"] for p in res["probabilities"])
    assert 0.95 <= prob_sum <= 1.05
    assert res["missing_vitals_count"] == 0
    assert len(res["contributing_factors"]) > 0


def test_triage_predict_critical_emergency():
    """Verify ML inference correctly escalates severe physiological distress."""
    payload = {
        "age": 68,
        "sex": "F",
        "arrival_mode": "ambulance",
        "chief_complaint_system": "cardiovascular",
        "mental_status_triage": "drowsy",
        "systolic_bp": 78.0,      # Hypotension / shock
        "diastolic_bp": 50.0,
        "heart_rate": 138.0,      # Severe tachycardia
        "respiratory_rate": 34.0,  # Tachypnea
        "temperature_c": 39.4,
        "spo2": 86.0,             # Critical Hypoxia
        "gcs_total": 12.0,
        "pain_score": 9.0,
        "num_comorbidities": 3,
        "comorbidities": ["hypertension", "heart failure", "diabetes_type2"],
        "model_type": "model_b_random_forest",
    }
    resp = client.post("/api/v1/models/predict", json=payload)
    assert resp.status_code == 200
    res = resp.json()
    # Should predict high urgency (Acuity 1 or 2)
    assert res["predicted_acuity"] <= 2
    assert res["urgency_tier"] == "HIGH"
    assert res["is_emergency"] is True

    factors_str = " ".join(res["contributing_factors"]).lower()
    assert "hypoxia" in factors_str or "spo2" in factors_str
    assert "shock" in factors_str or "hypotension" in factors_str or "tachycardia" in factors_str


def test_triage_predict_missing_vitals_resilience():
    """Verify model gracefully handles missing intake vitals via explicit indicator features."""
    payload = {
        "age": 45,
        "sex": "M",
        "arrival_mode": "walk-in",
        "chief_complaint_system": "gastrointestinal",
        "mental_status_triage": "alert",
        # Explicitly omitting blood pressure and respiratory rate
        "heart_rate": 80.0,
        "temperature_c": 37.0,
        "spo2": 97.0,
        "model_type": "model_b_random_forest",
    }
    resp = client.post("/api/v1/models/predict", json=payload)
    assert resp.status_code == 200
    res = resp.json()
    assert 1 <= res["predicted_acuity"] <= 5
    assert res["missing_vitals_count"] >= 2
    assert "systolic_bp" in res["missing_vitals"]
    assert "respiratory_rate" in res["missing_vitals"]


def test_models_evaluation_report():
    """Verify GET /api/v1/models/evaluation returns comparative benchmarks."""
    resp = client.get("/api/v1/models/evaluation")
    assert resp.status_code == 200
    report = resp.json()
    assert "champion_model" in report
    assert len(report["models"]) >= 4
    for model in report["models"]:
        assert "macro_f1" in model
        assert "balanced_accuracy" in model
        assert "confusion_matrix" in model
        assert model["macro_f1"] > 0.0
