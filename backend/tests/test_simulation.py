"""Test Suite for Monte Carlo OPD Queue Simulation & Comparative Policy Evaluation."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_empirical_calibration_baseline():
    """Verify empirical calibration from Hospital ER dataset."""
    resp = client.get("/api/v1/simulation/calibration")
    assert resp.status_code == 200
    data = resp.json()
    assert "empirical_mean_wait" in data
    assert 30.0 <= data["empirical_mean_wait"] <= 40.0
    assert data["total_records"] == 9216.0


def test_monte_carlo_simulation_execution():
    """Test executing multi-replication queue simulation across policies."""
    payload = {
        "num_doctors": 3,
        "shift_hours": 6.0,
        "arrival_rate_per_hour": 16.0,
        "replications": 8,
        "random_seed": 100,
    }
    resp = client.post("/api/v1/simulation/run", json=payload)
    assert resp.status_code == 200
    res = resp.json()

    assert "policies" in res
    assert len(res["policies"]) == 3

    policy_map = {p["policy_name"]: p for p in res["policies"]}
    assert "FCFS" in policy_map
    assert "CONVENTIONAL_PRIORITY" in policy_map
    assert "DYNAMIC_HYBRID" in policy_map

    fcfs = policy_map["FCFS"]
    conv = policy_map["CONVENTIONAL_PRIORITY"]
    hybrid = policy_map["DYNAMIC_HYBRID"]

    # 1. Clinical urgency benefit: Priority & Hybrid must serve Acuity 1 faster than FCFS
    assert hybrid["per_acuity_mean_wait"]["Acuity_1"] < fcfs["per_acuity_mean_wait"]["Acuity_1"]

    # 2. Starvation protection: Hybrid starvation count must be lower or equal to Conventional Priority
    assert hybrid["starvation_count"] <= conv["starvation_count"]

    # 3. Check 95% Confidence Interval consistency
    ci = hybrid["overall_mean_wait_mins"]
    assert ci["ci_lower"] <= ci["mean"] <= ci["ci_upper"]

    # 4. Throughput and utilization sanity checks
    assert hybrid["patients_served"] > 0
    assert 0.0 <= hybrid["doctor_utilization_pct"] <= 100.0


def test_get_simulation_results_cached():
    """Verify GET /api/v1/simulation/results returns latest report."""
    resp = client.get("/api/v1/simulation/results")
    assert resp.status_code == 200
    res = resp.json()
    assert res["recommended_policy"] == "DYNAMIC_HYBRID"
    assert len(res["policies"]) == 3
