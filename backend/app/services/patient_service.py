"""Patient registration, updating, search, and visit history services."""
import json
import random
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database.models import Patient, Visit, QueueItem
from app.schemas.patient import (
    PatientCreate,
    PatientUpdate,
    PatientResponse,
    VisitBase,
    VisitResponse,
)
from app.schemas.triage import TriageInput, PriorityFactor
from app.services.triage_service import calculate_triage_priority


def generate_patient_code(db: Session) -> str:
    """Generate a unique human-friendly patient code like PAT-1042."""
    while True:
        code = f"PAT-{random.randint(1000, 9999)}"
        exists = db.query(Patient).filter(Patient.patient_id == code).first()
        if not exists:
            return code


def parse_json_or_list(raw_value: Optional[str]) -> List[str]:
    """Safely parse stored JSON or delimited text into string list."""
    if not raw_value:
        return []
    try:
        data = json.loads(raw_value)
        if isinstance(data, list):
            return [str(x) for x in data]
        return [str(data)]
    except Exception:
        return [s.strip() for s in raw_value.split(",") if s.strip()]


def format_visit_response(visit: Visit) -> VisitResponse:
    """Transform Visit ORM model into VisitResponse Pydantic model."""
    symptoms = parse_json_or_list(visit.symptoms)
    diseases = parse_json_or_list(visit.previous_diseases)

    factors: List[PriorityFactor] = []
    if visit.risk_factors:
        try:
            raw_factors = json.loads(visit.risk_factors)
            if isinstance(raw_factors, list):
                for rf in raw_factors:
                    factors.append(PriorityFactor(**rf))
        except Exception:
            pass

    return VisitResponse(
        id=visit.id,
        visit_id=visit.visit_id,
        patient_id=visit.patient_id,
        visit_date=visit.visit_date,
        visit_time=visit.visit_time,
        symptoms=symptoms,
        temperature=visit.temperature,
        heart_rate=visit.heart_rate,
        spo2=visit.spo2,
        blood_pressure=visit.blood_pressure,
        sugar_level=visit.sugar_level,
        previous_diseases=diseases,
        priority_score=visit.priority_score,
        severity=visit.severity,
        risk_factors=factors,
        status=visit.status,
        created_at=visit.created_at,
    )


def format_patient_response(patient: Patient) -> PatientResponse:
    """Transform Patient ORM model into PatientResponse."""
    visits = [format_visit_response(v) for v in (patient.visits or [])]
    # Sort visits with newest first
    visits.sort(key=lambda v: v.created_at, reverse=True)

    chronic = parse_json_or_list(patient.chronic_conditions)

    return PatientResponse(
        id=patient.id,
        patient_id=patient.patient_id,
        full_name=patient.full_name,
        age=patient.age,
        gender=patient.gender,
        contact=patient.contact,
        emergency_contact=patient.emergency_contact,
        blood_group=patient.blood_group,
        address=patient.address,
        chronic_conditions=chronic,
        created_at=patient.created_at,
        updated_at=patient.updated_at,
        visits=visits,
    )


def create_patient(db: Session, payload: PatientCreate) -> PatientResponse:
    """Register a new patient and optional initial visit."""
    patient_code = payload.patient_id.strip() if payload.patient_id else generate_patient_code(db)

    # Check for duplicate patient code
    existing = db.query(Patient).filter(Patient.patient_id == patient_code).first()
    if existing:
        patient_code = generate_patient_code(db)

    chronic_str = json.dumps(payload.chronic_conditions or [])

    new_patient = Patient(
        patient_id=patient_code,
        full_name=payload.full_name,
        age=payload.age,
        gender=payload.gender,
        contact=payload.contact,
        emergency_contact=payload.emergency_contact,
        blood_group=payload.blood_group,
        address=payload.address,
        chronic_conditions=chronic_str,
    )
    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)

    # Add initial visit if provided
    if payload.initial_visit:
        add_patient_visit(db, new_patient.patient_id, payload.initial_visit)
        db.refresh(new_patient)

    return format_patient_response(new_patient)


def add_patient_visit(db: Session, patient_code: str, visit_data: VisitBase) -> VisitResponse:
    """Create a new clinical visit, compute AI triage score, and persist."""
    patient = db.query(Patient).filter(Patient.patient_id == patient_code).first()
    if not patient:
        raise ValueError(f"Patient with code {patient_code} not found")

    # Run AI Triage
    triage_input = TriageInput(
        age=patient.age,
        gender=patient.gender,
        symptoms=visit_data.symptoms or [],
        temperature=visit_data.temperature,
        heart_rate=visit_data.heart_rate,
        spo2=visit_data.spo2,
        blood_pressure=visit_data.blood_pressure,
        sugar_level=visit_data.sugar_level,
        previous_diseases=visit_data.previous_diseases or [],
    )
    triage_res = calculate_triage_priority(triage_input)

    now = datetime.now()
    visit_id = f"V_{int(now.timestamp() * 1000)}"
    visit_date = now.strftime("%Y-%m-%d")
    visit_time = now.strftime("%I:%M %p")

    risk_factors_json = json.dumps([f.model_dump() for f in triage_res.factors])

    new_visit = Visit(
        visit_id=visit_id,
        patient_id=patient.id,
        visit_date=visit_date,
        visit_time=visit_time,
        symptoms=json.dumps(visit_data.symptoms or []),
        temperature=visit_data.temperature,
        heart_rate=visit_data.heart_rate,
        spo2=visit_data.spo2,
        blood_pressure=visit_data.blood_pressure,
        sugar_level=visit_data.sugar_level,
        previous_diseases=json.dumps(visit_data.previous_diseases or []),
        priority_score=triage_res.priority_score,
        severity=triage_res.severity,
        risk_factors=risk_factors_json,
        status="WAITING",
    )
    db.add(new_visit)
    db.commit()
    db.refresh(new_visit)

    return format_visit_response(new_visit)


def get_patient_by_code(db: Session, patient_code: str) -> Optional[PatientResponse]:
    """Retrieve patient by ID code or integer PK."""
    patient = db.query(Patient).filter(Patient.patient_id == patient_code).first()
    if not patient and patient_code.isdigit():
        patient = db.query(Patient).filter(Patient.id == int(patient_code)).first()

    if not patient:
        return None
    return format_patient_response(patient)


def get_patients_list(
    db: Session, query: Optional[str] = None, skip: int = 0, limit: int = 100
) -> List[PatientResponse]:
    """Search and list patients."""
    q = db.query(Patient)
    if query:
        search_pattern = f"%{query}%"
        q = q.filter(
            or_(
                Patient.full_name.ilike(search_pattern),
                Patient.patient_id.ilike(search_pattern),
                Patient.contact.ilike(search_pattern),
            )
        )
    patients = q.order_by(Patient.created_at.desc()).offset(skip).limit(limit).all()
    return [format_patient_response(p) for p in patients]


def update_patient_record(
    db: Session, patient_code: str, payload: PatientUpdate
) -> Optional[PatientResponse]:
    """Update patient demographics or medical profile."""
    patient = db.query(Patient).filter(Patient.patient_id == patient_code).first()
    if not patient and patient_code.isdigit():
        patient = db.query(Patient).filter(Patient.id == int(patient_code)).first()

    if not patient:
        return None

    update_data = payload.model_dump(exclude_unset=True)
    if "chronic_conditions" in update_data:
        update_data["chronic_conditions"] = json.dumps(update_data["chronic_conditions"] or [])

    for field, val in update_data.items():
        setattr(patient, field, val)

    patient.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(patient)
    return format_patient_response(patient)
