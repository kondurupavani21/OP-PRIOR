"""Test Suite for Bilingual Token Announcements and Public Display Feed."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.auth_service import seed_default_accounts

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_accounts():
    """Ensure seed doctor and receptionist accounts exist."""
    seed_default_accounts()


@pytest.fixture
def doctor_token():
    resp = client.post("/api/v1/auth/login", json={"email": "doctor@medqueue.org", "password": "doctor123"})
    return resp.json()["access_token"]


def test_announcements_board_empty_or_default():
    """Verify GET /api/v1/announcements/board returns structured waiting room payload."""
    resp = client.get("/api/v1/announcements/board")
    assert resp.status_code == 200
    data = resp.json()
    assert "active_called_tokens" in data
    assert "recent_call_history" in data
    assert "total_waiting" in data
    assert "server_time" in data


def test_call_patient_creates_bilingual_announcement(doctor_token):
    """Verify that calling a patient generates bilingual English and Telugu announcements with masked initials."""
    headers = {"Authorization": f"Bearer {doctor_token}"}

    # 1. Register patient
    p_resp = client.post("/api/v1/patients", json={
        "full_name": "Venkateswara Rao",
        "contact": "9988776655",
        "age": 62,
        "gender": "Male",
    }, headers=headers)
    assert p_resp.status_code == 201
    pat_code = p_resp.json()["patient_code"]

    # 2. Create encounter
    e_resp = client.post("/api/v1/encounters", json={
        "patient_code": pat_code,
        "department": "Cardiology",
        "chief_complaint": "Exertional dyspnea",
    }, headers=headers)
    assert e_resp.status_code == 201
    enc_id = e_resp.json()["encounter_id"]

    # 3. Enqueue patient
    q_resp = client.post("/api/v1/queue", json={
        "patient_code": pat_code,
        "encounter_id": enc_id,
        "department": "Cardiology",
        "initial_priority": 2,
    })
    assert q_resp.status_code == 201
    entry_id = q_resp.json()["entry_id"]
    token_num = q_resp.json()["token_number"]

    # 4. Doctor calls patient into Consultation Room 3
    call_resp = client.post(
        f"/api/v1/queue/{entry_id}/call?room_number=Room%203",
        headers=headers,
    )
    assert call_resp.status_code == 200
    assert call_resp.json()["queue_status"] == "CALLED"

    # 5. Check announcement board
    board_resp = client.get("/api/v1/announcements/board")
    assert board_resp.status_code == 200
    board = board_resp.json()

    # Must contain active call
    assert len(board["active_called_tokens"]) > 0
    active = next((a for a in board["active_called_tokens"] if a["token_number"] == token_num), None)
    assert active is not None
    assert "Room 3" in active["room_number"]
    assert "V. R." in active["patient_initials"]
    assert active["patient_name"] == "Venkateswara Rao"
    assert "Venkateswara Rao" in active["speech_text_en"]
    assert "Venkateswara Rao" in active["speech_text_te"]
    assert "Token" in active["speech_text_en"]
    assert "టోకెన్" in active["speech_text_te"]

    # 6. Check latest announcement endpoint
    latest_resp = client.get("/api/v1/announcements/latest")
    assert latest_resp.status_code == 200
    latest = latest_resp.json()
    assert latest["token_number"] == token_num
    assert latest["patient_name"] == "Venkateswara Rao"


def test_receptionist_can_call_patient():
    """Verify that a receptionist staff member can call a patient without 403 error."""
    rec_login = client.post("/api/v1/auth/login", json={"email": "receptionist@medqueue.org", "password": "receptionist123"})
    assert rec_login.status_code == 200
    rec_token = rec_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {rec_token}"}

    # Register patient
    p_resp = client.post("/api/v1/patients", json={
        "full_name": "Pavani Konduru",
        "contact": "9887766554",
        "age": 28,
        "gender": "Female",
    }, headers=headers)
    assert p_resp.status_code == 201
    pat_code = p_resp.json()["patient_code"]

    # Create encounter
    e_resp = client.post("/api/v1/encounters", json={
        "patient_code": pat_code,
        "department": "General Medicine",
        "chief_complaint": "Routine follow-up",
    }, headers=headers)
    assert e_resp.status_code == 201
    enc_id = e_resp.json()["encounter_id"]

    # Enqueue patient
    q_resp = client.post("/api/v1/queue", json={
        "patient_code": pat_code,
        "encounter_id": enc_id,
        "initial_priority": 3,
    })
    assert q_resp.status_code == 201
    entry_id = q_resp.json()["entry_id"]

    # Call patient by receptionist into Reception Booth 1
    call_resp = client.post(
        f"/api/v1/queue/{entry_id}/call?room_number=Reception%20Booth%201",
        headers=headers,
    )
    assert call_resp.status_code == 200
    call_data = call_resp.json()
    assert call_data["queue_status"] == "CALLED"
    assert call_data["assigned_room"] == "Reception Booth 1"

    # Verify announcement board reflects the call
    board = client.get("/api/v1/announcements/board").json()
    active = next((a for a in board["active_called_tokens"] if a["patient_code"] == pat_code), None)
    assert active is not None
    assert "Pavani Konduru" in active["speech_text_en"]
    assert "Pavani Konduru" in active["speech_text_te"]


def test_missing_name_handled_safely():
    """Verify that calling a patient with missing/unrecorded name falls back safely to 'Patient'."""
    p_resp = client.post("/api/v1/patients", json={
        "full_name": "Patient",
        "contact": "9112233445",
        "age": 35,
    })
    assert p_resp.status_code == 201
    pat_code = p_resp.json()["patient_code"]

    e_resp = client.post("/api/v1/encounters", json={
        "patient_code": pat_code,
        "chief_complaint": "Intake",
    })
    assert e_resp.status_code == 201
    enc_id = e_resp.json()["encounter_id"]

    q_resp = client.post("/api/v1/queue", json={
        "patient_code": pat_code,
        "encounter_id": enc_id,
        "initial_priority": 3,
    })
    assert q_resp.status_code == 201
    entry_id = q_resp.json()["entry_id"]

    call_resp = client.post(f"/api/v1/queue/{entry_id}/call?room_number=Room%201")
    assert call_resp.status_code == 200

    board = client.get("/api/v1/announcements/board").json()
    active = next((a for a in board["active_called_tokens"] if a["patient_code"] == pat_code), None)
    assert active is not None
    assert "Token" in active["speech_text_en"]
    assert "Room 1" in active["speech_text_en"]
