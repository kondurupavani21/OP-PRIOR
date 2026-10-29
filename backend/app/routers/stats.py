"""Clinic operations and daily statistics router."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.database.models import Patient, Visit, QueueItem, Consultation
from app.services.queue_service import get_today_date_str
from app.database.mongodb import (
    get_queue_entries_col,
    get_encounters_col,
)

router = APIRouter(prefix="/stats", tags=["Dashboard Statistics"])


class DailyStatsResponse(BaseModel):
    """Daily clinic operations statistics."""
    date: str = Field(description="Date in YYYY-MM-DD")
    total_patients_today: int = Field(description="Patients registered today")
    waiting_count: int = Field(description="Currently waiting in queue")
    in_consultation_count: int = Field(description="Currently with doctor")
    emergency_count: int = Field(description="High-priority or emergency cases today")
    consulted_today_count: int = Field(description="Consultations concluded today")
    average_wait_mins: int = Field(description="Estimated average waiting time")


@router.get(
    "/daily",
    response_model=DailyStatsResponse,
    summary="Daily clinic operations KPI stats",
    description="Provides real-time summary statistics for dashboard cards matching MedQueue AI UI.",
)
def get_daily_statistics(
    date: Optional[str] = Query(default=None, description="Date YYYY-MM-DD (defaults to today)"),
    db: Session = Depends(get_db),
) -> DailyStatsResponse:
    """Compute live dashboard metrics derived consistently from MongoDB active queue."""
    target_date = date or get_today_date_str()
    today_compact = target_date.replace("-", "")

    # Query MongoDB queue entries (Primary operational queue)
    mongo_q_col = get_queue_entries_col()
    mongo_items = list(mongo_q_col.find({
        "queue_status": {"$in": ["WAITING", "CALLED", "IN_CONSULTATION", "COMPLETED"]}
    }))

    if mongo_items or mongo_q_col.count_documents({}) > 0:
        waiting_count = sum(1 for q in mongo_items if q.get("queue_status") == "WAITING")
        in_consultation_count = sum(1 for q in mongo_items if q.get("queue_status") in ["CALLED", "IN_CONSULTATION"])
        emergency_count = sum(
            1 for q in mongo_items
            if (q.get("queue_status") in ["WAITING", "CALLED", "IN_CONSULTATION"]) and
            (q.get("is_emergency") or q.get("clinician_approved_priority") == 1 or q.get("recommended_priority") == 1)
        )
        consulted_today = sum(
            1 for q in mongo_items
            if q.get("queue_status") == "COMPLETED" and str(q.get("entry_id", "")).startswith(f"Q-{today_compact}")
        )

        enc_col = get_encounters_col()
        total_patients = enc_col.count_documents({
            "created_at": {"$regex": f"^{target_date}"}
        })
        if total_patients == 0:
            total_patients = len(mongo_items)

        avg_wait = 15
        if waiting_count > 0:
            avg_wait = min(60, max(5, waiting_count * 10))

        return DailyStatsResponse(
            date=target_date,
            total_patients_today=total_patients,
            waiting_count=waiting_count,
            in_consultation_count=in_consultation_count,
            emergency_count=emergency_count,
            consulted_today_count=consulted_today,
            average_wait_mins=avg_wait,
        )

    # Fallback to SQLite if MongoDB has no entries
    total_patients = (
        db.query(Visit)
        .filter(Visit.visit_date == target_date)
        .count()
    )

    active_items = (
        db.query(QueueItem)
        .filter(QueueItem.queue_date == target_date)
        .all()
    )

    waiting_count = sum(1 for q in active_items if q.status == "WAITING")
    in_consultation_count = sum(1 for q in active_items if q.status == "WITH_DOCTOR")
    emergency_count = sum(
        1 for q in active_items if q.severity == "HIGH" or q.priority_score >= 80
    )

    consulted_count = (
        db.query(Consultation)
        .filter(Consultation.consultation_date == target_date)
        .count()
    )

    avg_wait = int(sum(q.estimated_wait_mins for q in active_items if q.status == "WAITING") / max(1, waiting_count))

    return DailyStatsResponse(
        date=target_date,
        total_patients_today=total_patients,
        waiting_count=waiting_count,
        in_consultation_count=in_consultation_count,
        emergency_count=emergency_count,
        consulted_today_count=consulted_count,
        average_wait_mins=avg_wait,
    )
