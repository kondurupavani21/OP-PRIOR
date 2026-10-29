"""Integration tests for Queue Management Engine, Scheduling Policies, and Doctor Overrides."""
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.auth_service import seed_default_accounts

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_accounts():
    seed_default_accounts()


def get_doctor_token() -> str:
    resp = client.post("/api/v1/auth/login", json={"email": "doctor@medqueue.org", "password": "doctor123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def create_patient_and_encounter(name: str, priority_hint: int = 3, is_emergency: bool = False) -> tuple:
    """Helper creating a test patient and encounter."""
    phone = f"9{uuid.uuid4().int % 1000000000:09d}"
    p_resp = client.post("/api/v1/patients", json={
        "full_name": name,
        "age": 40,
        "gender": "Female",
        "contact": phone,
    })
    p_code = p_resp.json()["patient_code"]

    vitals = {
        "temperature": 98.6,
        "heart_rate": 75,
        "systolic_bp": 120,
        "diastolic_bp": 80,
        "spo2": 85.0 if is_emergency else 98.0,
    }

    e_resp = client.post("/api/v1/encounters", json={
        "patient_code": p_code,
        "chief_complaint": "Acute emergency check" if is_emergency else "General checkup",
        "vitals": vitals,
    })
    e_id = e_resp.json()["encounter_id"]
    return p_code, e_id


def test_enqueue_and_token_generation():
    """Verify enqueuing generates sequential tokens and initial WAITING status."""
    p_code, e_id = create_patient_and_encounter("Test Patient One", priority_hint=3)

    resp = client.post("/api/v1/queue", json={
        "patient_code": p_code,
        "encounter_id": e_id,
        "initial_priority": 3,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["token_number"] >= 1
    assert data["queue_status"] == "WAITING"
    assert data["patient_code"] == p_code


def test_queue_policies_ordering():
    """Compare FCFS, Conventional Priority, and Dynamic Hybrid queue ordering."""
    # Create Low Urgency patient (Level 5) first
    p1, e1 = create_patient_and_encounter("Low Urgency Patient", priority_hint=5)
    client.post("/api/v1/queue", json={"patient_code": p1, "encounter_id": e1, "initial_priority": 5})

    # Create Urgent patient (Level 2) second
    p2, e2 = create_patient_and_encounter("Urgent Patient", priority_hint=2)
    client.post("/api/v1/queue", json={"patient_code": p2, "encounter_id": e2, "initial_priority": 2})

    # Under Conventional Priority, Level 2 must precede Level 5
    conv_queue = client.get("/api/v1/queue?policy=CONVENTIONAL_PRIORITY").json()
    level2_pos = next(q["current_position"] for q in conv_queue if q["patient_code"] == p2)
    level5_pos = next(q["current_position"] for q in conv_queue if q["patient_code"] == p1)
    assert level2_pos < level5_pos

    # Under FCFS, arrival order dictates service (Level 5 arrived first)
    fcfs_queue = client.get("/api/v1/queue?policy=FCFS").json()
    p1_fcfs_pos = next(q["current_position"] for q in fcfs_queue if q["patient_code"] == p1)
    p2_fcfs_pos = next(q["current_position"] for q in fcfs_queue if q["patient_code"] == p2)
    assert p1_fcfs_pos < p2_fcfs_pos


def test_emergency_bypass_across_all_policies():
    """Verify clinical emergency case always jumps to position 1 across all policies."""
    p_stable, e_stable = create_patient_and_encounter("Stable Patient", priority_hint=3)
    client.post("/api/v1/queue", json={"patient_code": p_stable, "encounter_id": e_stable, "initial_priority": 3})

    p_emerg, e_emerg = create_patient_and_encounter("Critical Emergency Patient", is_emergency=True)
    client.post("/api/v1/queue", json={"patient_code": p_emerg, "encounter_id": e_emerg, "initial_priority": 1})

    for policy in ["FCFS", "CONVENTIONAL_PRIORITY", "DYNAMIC_HYBRID"]:
        q = client.get(f"/api/v1/queue?policy={policy}").json()
        emerg_item = next(item for item in q if item["patient_code"] == p_emerg)
        assert emerg_item["is_emergency"] is True
        assert emerg_item["current_position"] == 1


def test_doctor_override_and_consultation_lifecycle():
    """Test doctor override of priority and consultation state progression."""
    token = get_doctor_token()
    p_code, e_id = create_patient_and_encounter("Patient for Override", priority_hint=4)
    enq_resp = client.post("/api/v1/queue", json={"patient_code": p_code, "encounter_id": e_id, "initial_priority": 4})
    entry_id = enq_resp.json()["entry_id"]

    # 1. Doctor overrides priority from Level 4 to Level 2
    override_resp = client.post(
        f"/api/v1/queue/{entry_id}/override",
        json={
            "new_priority": 2,
            "override_reason": "Patient exhibiting clinical signs of chest pain and acute distress.",
            "clinical_rationale": "Elevated risk profile upon physical observation.",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert override_resp.status_code == 200
    ov_data = override_resp.json()
    assert ov_data["clinician_approved_priority"] == 2
    assert ov_data["is_overridden"] is True

    # 2. Call patient
    call_resp = client.post(
        f"/api/v1/queue/{entry_id}/call?room_number=Room-2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert call_resp.status_code == 200
    assert call_resp.json()["queue_status"] == "CALLED"
    assert call_resp.json()["assigned_room"] == "Room-2"

    # 3. Start consultation
    start_resp = client.post(
        f"/api/v1/queue/{entry_id}/start",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert start_resp.status_code == 200
    assert start_resp.json()["queue_status"] == "IN_CONSULTATION"

    # 4. Complete consultation
    comp_resp = client.post(
        f"/api/v1/queue/{entry_id}/complete",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert comp_resp.status_code == 200
    assert comp_resp.json()["queue_status"] == "COMPLETED"
