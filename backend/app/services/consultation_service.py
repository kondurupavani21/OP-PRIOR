"""Consultation service for documenting clinical diagnoses and prescriptions."""
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from app.database.models import Consultation, Patient, QueueItem
from app.schemas.consultation import ConsultationCreate, ConsultationResponse


def create_consultation(db: Session, payload: ConsultationCreate) -> ConsultationResponse:
    """Record a completed doctor consultation and retire the patient from active queue."""
    patient = db.query(Patient).filter(Patient.patient_id == payload.patient_id).first()
    if not patient and payload.patient_id.isdigit():
        patient = db.query(Patient).filter(Patient.id == int(payload.patient_id)).first()

    if not patient:
        raise ValueError(f"Patient with code {payload.patient_id} not found.")

    now = datetime.now()
    consult_date = now.strftime("%Y-%m-%d")
    consult_time = now.strftime("%I:%M %p")

    consultation = Consultation(
        patient_id=patient.id,
        doctor_name=payload.doctor_name or "Dr. Assigned",
        consultation_date=consult_date,
        consultation_time=consult_time,
        diagnosis=payload.diagnosis,
        symptoms=payload.symptoms,
        prescription=payload.prescription,
        vital_signs=payload.vital_signs,
        notes=payload.notes,
        follow_up_date=payload.follow_up_date,
    )
    db.add(consultation)

    # Mark active queue item as COMPLETED
    active_queue = (
        db.query(QueueItem)
        .filter(
            QueueItem.patient_id == patient.id,
            QueueItem.status.in_(["WAITING", "WITH_DOCTOR"]),
        )
        .all()
    )
    for q in active_queue:
        q.status = "COMPLETED"
        q.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(consultation)

    resp = ConsultationResponse.model_validate(consultation)
    resp.patient_code = patient.patient_id
    return resp


def get_consultations_by_patient(
    db: Session, patient_code: str
) -> List[ConsultationResponse]:
    """Retrieve full consultation history for a given patient."""
    patient = db.query(Patient).filter(Patient.patient_id == patient_code).first()
    if not patient and patient_code.isdigit():
        patient = db.query(Patient).filter(Patient.id == int(patient_code)).first()

    if not patient:
        return []

    consults = (
        db.query(Consultation)
        .filter(Consultation.patient_id == patient.id)
        .order_by(Consultation.created_at.desc())
        .all()
    )
    results = []
    for c in consults:
        r = ConsultationResponse.model_validate(c)
        r.patient_code = patient.patient_id
        results.append(r)
    return results


def list_recent_consultations(
    db: Session, date_str: Optional[str] = None, limit: int = 50
) -> List[ConsultationResponse]:
    """List recent clinic consultations with optional date filter."""
    q = db.query(Consultation)
    if date_str:
        q = q.filter(Consultation.consultation_date == date_str)
    consults = q.order_by(Consultation.created_at.desc()).limit(limit).all()

    results = []
    for c in consults:
        r = ConsultationResponse.model_validate(c)
        if c.patient:
            r.patient_code = c.patient.patient_id
        results.append(r)
    return results
