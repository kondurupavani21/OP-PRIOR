"""Queue management service: token allocation, priority ordering, calling patients."""
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database.models import QueueItem, Patient, Visit
from app.schemas.queue import (
    QueueItemCreate,
    QueueItemUpdate,
    QueueItemResponse,
    QueueSeveritySummary,
)


def get_today_date_str() -> str:
    """Format today's calendar date as YYYY-MM-DD."""
    return datetime.now().strftime("%Y-%m-%d")


def calculate_wait_times(queue_items: List[QueueItem]) -> None:
    """Recalculate dynamic wait times (in minutes) based on queue order."""
    accumulated_mins = 0
    for item in queue_items:
        if item.status == "WITH_DOCTOR":
            item.estimated_wait_mins = 0
        elif item.status == "WAITING":
            item.estimated_wait_mins = accumulated_mins
            # Higher acuity patients take slightly longer physician review
            duration = 15 if item.severity == "HIGH" else (10 if item.severity == "MEDIUM" else 7)
            accumulated_mins += duration


def add_to_queue(db: Session, payload: QueueItemCreate) -> QueueItemResponse:
    """Add a patient to the current day's active consultation queue."""
    patient = db.query(Patient).filter(Patient.patient_id == payload.patient_id).first()
    if not patient and payload.patient_id.isdigit():
        patient = db.query(Patient).filter(Patient.id == int(payload.patient_id)).first()

    if not patient:
        raise ValueError(f"Patient with ID {payload.patient_id} does not exist.")

    today_str = get_today_date_str()

    # Check if patient is already waiting or with doctor today
    active_entry = (
        db.query(QueueItem)
        .filter(
            QueueItem.patient_id == patient.id,
            QueueItem.queue_date == today_str,
            QueueItem.status.in_(["WAITING", "WITH_DOCTOR"]),
        )
        .first()
    )
    if active_entry:
        return QueueItemResponse.model_validate(active_entry)

    # Next sequential token for today
    max_token = (
        db.query(func.max(QueueItem.token_number))
        .filter(QueueItem.queue_date == today_str)
        .scalar()
    ) or 0
    next_token = max_token + 1

    # Retrieve latest visit for triage metrics
    latest_visit = (
        db.query(Visit)
        .filter(Visit.patient_id == patient.id)
        .order_by(Visit.created_at.desc())
        .first()
    )

    priority_score = latest_visit.priority_score if latest_visit else 20
    severity = latest_visit.severity if latest_visit else "LOW"
    visit_id = latest_visit.id if latest_visit else None

    # Estimate initial wait time based on waiting queue length
    waiting_count = (
        db.query(QueueItem)
        .filter(
            QueueItem.queue_date == today_str,
            QueueItem.status == "WAITING",
        )
        .count()
    )
    est_wait = waiting_count * 10

    queue_item = QueueItem(
        token_number=next_token,
        patient_id=patient.id,
        visit_id=visit_id,
        patient_name=patient.full_name,
        patient_code=patient.patient_id,
        priority_score=priority_score,
        severity=severity,
        status="WAITING",
        queue_date=today_str,
        assigned_doctor=payload.assigned_doctor,
        assigned_room=payload.assigned_room,
        estimated_wait_mins=est_wait,
    )
    db.add(queue_item)
    db.commit()
    db.refresh(queue_item)

    return QueueItemResponse.model_validate(queue_item)


def get_active_queue(
    db: Session,
    date_str: Optional[str] = None,
    sort_by: str = "priority",  # 'priority' or 'fifo'
) -> List[QueueItemResponse]:
    """Fetch active queue sorted by priority score (high to low) or FIFO token order."""
    target_date = date_str or get_today_date_str()

    query = db.query(QueueItem).filter(
        QueueItem.queue_date == target_date,
        QueueItem.status.in_(["WAITING", "WITH_DOCTOR"]),
    )

    if sort_by == "priority":
        # Sort WITH_DOCTOR first, then highest priority score, then earliest check in
        items = query.all()
        # Sort logic: WITH_DOCTOR on top, then descending priority score, then check-in time
        items.sort(
            key=lambda x: (
                0 if x.status == "WITH_DOCTOR" else 1,
                -x.priority_score,
                x.token_number,
            )
        )
    else:
        # Strict FIFO token order
        items = query.order_by(QueueItem.token_number.asc()).all()

    calculate_wait_times(items)
    return [QueueItemResponse.model_validate(it) for it in items]


def update_queue_status(
    db: Session,
    queue_id: int,
    payload: QueueItemUpdate,
) -> Optional[QueueItemResponse]:
    """Update status (e.g. WITH_DOCTOR, COMPLETED) or doctor/room assignment."""
    item = db.query(QueueItem).filter(QueueItem.id == queue_id).first()
    if not item:
        return None

    now_utc = datetime.now(timezone.utc)
    if payload.status:
        new_status = payload.status.upper()
        item.status = new_status
        if new_status == "WITH_DOCTOR" and not item.called_at:
            item.called_at = now_utc
        elif new_status in ["COMPLETED", "CANCELLED"]:
            item.completed_at = now_utc

    if payload.assigned_doctor is not None:
        item.assigned_doctor = payload.assigned_doctor
    if payload.assigned_room is not None:
        item.assigned_room = payload.assigned_room
    if payload.estimated_wait_mins is not None:
        item.estimated_wait_mins = payload.estimated_wait_mins

    db.commit()
    db.refresh(item)
    return QueueItemResponse.model_validate(item)


def call_next_patient(
    db: Session,
    doctor_name: Optional[str] = "Dr. On Duty",
    room_number: Optional[str] = "OPD-1",
) -> Optional[QueueItemResponse]:
    """Find the highest-urgency waiting patient and call them into consultation."""
    today_str = get_today_date_str()

    waiting_items = (
        db.query(QueueItem)
        .filter(
            QueueItem.queue_date == today_str,
            QueueItem.status == "WAITING",
        )
        .all()
    )

    if not waiting_items:
        return None

    # Pick patient with highest priority score, tie-break by earlier token
    waiting_items.sort(key=lambda x: (-x.priority_score, x.token_number))
    next_patient_item = waiting_items[0]

    now_utc = datetime.now(timezone.utc)
    next_patient_item.status = "WITH_DOCTOR"
    next_patient_item.called_at = now_utc
    if doctor_name:
        next_patient_item.assigned_doctor = doctor_name
    if room_number:
        next_patient_item.assigned_room = room_number

    db.commit()
    db.refresh(next_patient_item)
    return QueueItemResponse.model_validate(next_patient_item)


def get_queue_summary(db: Session, date_str: Optional[str] = None) -> QueueSeveritySummary:
    """Calculate queue summary and acuity breakdown for current day."""
    target_date = date_str or get_today_date_str()

    active_items = (
        db.query(QueueItem)
        .filter(
            QueueItem.queue_date == target_date,
            QueueItem.status.in_(["WAITING", "WITH_DOCTOR"]),
        )
        .all()
    )

    total = len(active_items)
    high = sum(1 for it in active_items if it.severity == "HIGH")
    medium = sum(1 for it in active_items if it.severity == "MEDIUM")
    low = sum(1 for it in active_items if it.severity == "LOW")
    emergency = sum(1 for it in active_items if it.severity == "HIGH" or it.priority_score >= 80)

    return QueueSeveritySummary(
        total=total,
        high=high,
        medium=medium,
        low=low,
        emergency_count=emergency,
        active_tokens=total,
    )
