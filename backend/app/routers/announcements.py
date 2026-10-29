"""Bilingual Token Announcements and Public Waiting Room Display Router."""
from datetime import datetime, timezone
import logging
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, status

from app.database.mongodb import (
    get_announcement_events_col,
    get_queue_entries_col,
    get_patients_col,
)

logger = logging.getLogger("medqueue.routers.announcements")
router = APIRouter(prefix="/announcements", tags=["Token Announcements & Public Display"])


class AnnouncementItem(BaseModel):
    """Detailed announcement payload with bilingual speech synthesis scripts."""
    event_id: str
    token_number: int
    token_display: str
    patient_code: str
    patient_initials: str
    patient_name: str
    room_number: str
    department: str
    doctor_name: str
    timestamp: str
    speech_text_en: str
    speech_text_te: str


class AnnouncementsBoardResponse(BaseModel):
    """Real-time data feed for outpatient waiting room screens."""
    current_announcement: Optional[AnnouncementItem] = None
    active_called_tokens: List[AnnouncementItem] = Field(default_factory=list)
    recent_call_history: List[AnnouncementItem] = Field(default_factory=list)
    total_waiting: int = 0
    server_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def get_initials(name: str) -> str:
    """Generate masked initials for patient privacy on public displays."""
    parts = name.strip().split()
    if not parts:
        return "PT"
    if len(parts) == 1:
        return f"{parts[0][0].upper()}."
    return f"{parts[0][0].upper()}. {parts[-1][0].upper()}."


def build_announcement_item(event_doc: dict) -> AnnouncementItem:
    """Transform MongoDB event document into bilingual announcement item."""
    token_num = event_doc.get("token_number", 1)
    patient_code = event_doc.get("patient_code", "PAT-000")
    room = event_doc.get("room_number", "OPD Room 1")

    # Fetch patient details for name (check event_doc, then queue_entries, then patients collection)
    full_name = event_doc.get("patient_name")
    if not full_name:
        q_entry = get_queue_entries_col().find_one({"$or": [{"patient_code": patient_code}, {"token_number": token_num}]}) or {}
        full_name = q_entry.get("patient_name")
    if not full_name:
        pat = get_patients_col().find_one({"patient_code": patient_code}) or {}
        full_name = pat.get("full_name", "Patient")

    initials = get_initials(full_name)

    # Fetch queue entry for department/doctor
    q_entry = get_queue_entries_col().find_one({"token_number": token_num}) or {}
    dept = q_entry.get("department", "General Medicine")
    doctor = q_entry.get("called_by", "Consulting Physician")

    # Format consistent patient token (e.g., Token P1005, Token PAT-1001, Token T-001)
    if patient_code and (patient_code.startswith("P") or patient_code.startswith("PAT")):
        token_display = f"Token {patient_code}"
    else:
        token_display = f"Token T-{token_num:03d}"

    # Room localization for natural Telugu cadence
    room_te = room.replace("OPD Room", "ఓపీడీ రూమ్").replace("Consultation Room", "కన్సల్టేషన్ రూమ్").replace("Room", "రూమ్")

    # Bilingual Speech Texts including Patient Name and Token
    if full_name and full_name != "Patient":
        speech_en = f"{token_display}. Patient {full_name}, please proceed to {room}."
        speech_te = f"టోకెన్ {patient_code if patient_code else f'T-{token_num:03d}'}. {full_name} గారు, దయచేసి {room_te} కి వెళ్లండి."
    else:
        speech_en = f"{token_display}. Please proceed to {room}."
        speech_te = f"టోకెన్ {patient_code if patient_code else f'T-{token_num:03d}'}. దయచేసి {room_te} కి వెళ్లండి."

    return AnnouncementItem(
        event_id=str(event_doc.get("event_id") or event_doc.get("_id")),
        token_number=token_num,
        token_display=token_display,
        patient_code=patient_code,
        patient_initials=initials,
        patient_name=full_name,
        room_number=room,
        department=dept,
        doctor_name=doctor,
        timestamp=event_doc.get("timestamp", datetime.now(timezone.utc).isoformat()),
        speech_text_en=speech_en,
        speech_text_te=speech_te,
    )


@router.get(
    "/board",
    response_model=AnnouncementsBoardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Public Waiting Room Display Feed",
)
def get_waiting_room_board() -> AnnouncementsBoardResponse:
    """Fetch current called tokens, recent call history, and queue depth for waiting room displays."""
    # 1. Fetch currently CALLED patients from active queue
    called_docs = list(get_queue_entries_col().find({"queue_status": "CALLED"}).sort("called_at", -1))
    active_called: List[AnnouncementItem] = []
    for c in called_docs:
        c_pcode = c.get("patient_code", "PAT-000")
        c_tok_num = c.get("token_number", 1)
        c_tok_disp = f"Token {c_pcode}" if (c_pcode.startswith("P") or c_pcode.startswith("PAT")) else f"Token T-{c_tok_num:03d}"
        c_name = c.get("patient_name", "Patient")
        c_room = c.get("assigned_room", "OPD Room 1")
        c_room_te = c_room.replace("OPD Room", "ఓపీడీ రూమ్").replace("Consultation Room", "కన్సల్టేషన్ రూమ్").replace("Room", "రూమ్")

        if c_name and c_name != "Patient":
            c_speech_en = f"{c_tok_disp}. Patient {c_name}, please proceed to {c_room}."
            c_speech_te = f"టోకెన్ {c_pcode if c_pcode else f'T-{c_tok_num:03d}'}. {c_name} గారు, దయచేసి {c_room_te} కి వెళ్లండి."
        else:
            c_speech_en = f"{c_tok_disp}. Please proceed to {c_room}."
            c_speech_te = f"టోకెన్ {c_pcode if c_pcode else f'T-{c_tok_num:03d}'}. దయచేసి {c_room_te} కి వెళ్లండి."

        active_called.append(AnnouncementItem(
            event_id=f"EVT-{c.get('entry_id')}",
            token_number=c_tok_num,
            token_display=c_tok_disp,
            patient_code=c_pcode,
            patient_initials=get_initials(c_name),
            patient_name=c_name,
            room_number=c_room,
            department=c.get("department", "General Medicine"),
            doctor_name=c.get("called_by", "Doctor"),
            timestamp=c.get("called_at", datetime.now(timezone.utc).isoformat()),
            speech_text_en=c_speech_en,
            speech_text_te=c_speech_te,
        ))

    # 2. Fetch recent announcement events
    events = list(get_announcement_events_col().find().sort("timestamp", -1).limit(10))
    recent_history = [build_announcement_item(ev) for ev in events]

    current_announcement = active_called[0] if active_called else (recent_history[0] if recent_history else None)
    total_waiting = get_queue_entries_col().count_documents({"queue_status": "WAITING"})

    return AnnouncementsBoardResponse(
        current_announcement=current_announcement,
        active_called_tokens=active_called,
        recent_call_history=recent_history,
        total_waiting=total_waiting,
        server_time=datetime.now(timezone.utc).isoformat(),
    )


@router.get(
    "/latest",
    response_model=Optional[AnnouncementItem],
    status_code=status.HTTP_200_OK,
    summary="Get Most Recent Token Announcement",
)
def get_latest_announcement() -> Optional[AnnouncementItem]:
    """Fetch latest announced token event."""
    last_event = get_announcement_events_col().find_one(sort=[("timestamp", -1)])
    if not last_event:
        return None
    return build_announcement_item(last_event)
