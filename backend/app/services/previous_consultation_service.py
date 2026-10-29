"""Service managing patient-reported and extracted previous consultations."""
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from app.database.mongodb import (
    get_previous_consultations_col,
    get_patients_col,
    get_audit_events_col,
)
from app.schemas.previous_consultation import (
    PreviousConsultationCreate,
    PreviousConsultationUpdate,
    PreviousConsultationResponse,
    utc_iso_now,
)


def create_previous_consultation(payload: PreviousConsultationCreate) -> PreviousConsultationResponse:
    """Record an external previous consultation for a patient."""
    patient = get_patients_col().find_one({"patient_code": payload.patient_code})
    if not patient:
        raise ValueError(f"Patient with code '{payload.patient_code}' not found.")

    cid = f"PCON-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    now_iso = utc_iso_now()

    doc = {
        "consultation_id": cid,
        "patient_code": payload.patient_code,
        "encounter_id": payload.encounter_id,
        "facility_name": payload.facility_name,
        "doctor_name": payload.doctor_name,
        "consultation_date": payload.consultation_date,
        "previous_symptoms": payload.previous_symptoms or [],
        "previous_diagnosis": payload.previous_diagnosis,
        "previous_investigations": payload.previous_investigations or [],
        "treatment_prescribed": payload.treatment_prescribed,
        "medicines_taken": payload.medicines_taken or [],
        "duration_of_treatment": payload.duration_of_treatment,
        "treatment_response": payload.treatment_response or "UNCHANGED",
        "side_effects_reported": payload.side_effects_reported,
        "source_provenance": payload.source_provenance or "PATIENT_REPORTED",
        "is_verified": False,
        "verified_by": None,
        "verified_at": None,
        "notes": payload.notes,
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    get_previous_consultations_col().insert_one(doc)

    # Log audit event
    get_audit_events_col().insert_one({
        "audit_id": f"AUD-{uuid.uuid4().hex[:10]}",
        "action": "PREVIOUS_CONSULTATION_RECORDED",
        "resource_type": "previous_consultation",
        "resource_id": cid,
        "timestamp": now_iso,
        "details": f"Recorded previous consultation at {payload.facility_name or 'external facility'} for {payload.patient_code}",
    })

    return PreviousConsultationResponse(**doc)


def get_patient_previous_consultations(patient_code: str) -> List[PreviousConsultationResponse]:
    """Retrieve all external previous consultations recorded for a patient."""
    col = get_previous_consultations_col()
    cursor = col.find({"patient_code": patient_code}).sort("consultation_date", -1)
    results: List[PreviousConsultationResponse] = []
    for doc in cursor:
        results.append(PreviousConsultationResponse(
            consultation_id=doc["consultation_id"],
            patient_code=doc["patient_code"],
            encounter_id=doc.get("encounter_id"),
            facility_name=doc.get("facility_name"),
            doctor_name=doc.get("doctor_name"),
            consultation_date=doc.get("consultation_date"),
            previous_symptoms=doc.get("previous_symptoms", []),
            previous_diagnosis=doc.get("previous_diagnosis"),
            previous_investigations=doc.get("previous_investigations", []),
            treatment_prescribed=doc.get("treatment_prescribed"),
            medicines_taken=doc.get("medicines_taken", []),
            duration_of_treatment=doc.get("duration_of_treatment"),
            treatment_response=doc.get("treatment_response", "UNCHANGED"),
            side_effects_reported=doc.get("side_effects_reported"),
            source_provenance=doc.get("source_provenance", "PATIENT_REPORTED"),
            is_verified=doc.get("is_verified", False),
            verified_by=doc.get("verified_by"),
            verified_at=doc.get("verified_at"),
            notes=doc.get("notes"),
            created_at=doc.get("created_at", utc_iso_now()),
            updated_at=doc.get("updated_at", utc_iso_now()),
        ))
    return results


def get_previous_consultation_by_id(consultation_id: str) -> Optional[PreviousConsultationResponse]:
    """Retrieve previous consultation by ID."""
    col = get_previous_consultations_col()
    doc = col.find_one({"consultation_id": consultation_id})
    if not doc:
        return None
    return PreviousConsultationResponse(
        consultation_id=doc["consultation_id"],
        patient_code=doc["patient_code"],
        encounter_id=doc.get("encounter_id"),
        facility_name=doc.get("facility_name"),
        doctor_name=doc.get("doctor_name"),
        consultation_date=doc.get("consultation_date"),
        previous_symptoms=doc.get("previous_symptoms", []),
        previous_diagnosis=doc.get("previous_diagnosis"),
        previous_investigations=doc.get("previous_investigations", []),
        treatment_prescribed=doc.get("treatment_prescribed"),
        medicines_taken=doc.get("medicines_taken", []),
        duration_of_treatment=doc.get("duration_of_treatment"),
        treatment_response=doc.get("treatment_response", "UNCHANGED"),
        side_effects_reported=doc.get("side_effects_reported"),
        source_provenance=doc.get("source_provenance", "PATIENT_REPORTED"),
        is_verified=doc.get("is_verified", False),
        verified_by=doc.get("verified_by"),
        verified_at=doc.get("verified_at"),
        notes=doc.get("notes"),
        created_at=doc.get("created_at", utc_iso_now()),
        updated_at=doc.get("updated_at", utc_iso_now()),
    )


def update_previous_consultation(
    consultation_id: str,
    payload: PreviousConsultationUpdate,
    verifier_id: Optional[str] = None,
) -> PreviousConsultationResponse:
    """Update fields or verify an existing previous consultation record."""
    col = get_previous_consultations_col()
    doc = col.find_one({"consultation_id": consultation_id})
    if not doc:
        raise ValueError(f"Previous consultation '{consultation_id}' not found.")

    now_iso = utc_iso_now()
    updates: Dict[str, Any] = {"updated_at": now_iso}

    for k, v in payload.model_dump(exclude_unset=True).items():
        if k == "is_verified" and v is True:
            updates["is_verified"] = True
            updates["verified_by"] = verifier_id
            updates["verified_at"] = now_iso
            updates["source_provenance"] = "CLINICIAN_VERIFIED"
        else:
            updates[k] = v

    col.update_one({"consultation_id": consultation_id}, {"$set": updates})

    # Log audit event
    get_audit_events_col().insert_one({
        "audit_id": f"AUD-{uuid.uuid4().hex[:10]}",
        "action": "PREVIOUS_CONSULTATION_UPDATED",
        "resource_type": "previous_consultation",
        "resource_id": consultation_id,
        "timestamp": now_iso,
        "details": f"Updated previous consultation {consultation_id} by {verifier_id or 'staff'}",
    })

    return get_previous_consultation_by_id(consultation_id)


def delete_previous_consultation(consultation_id: str) -> bool:
    """Delete an external previous consultation record by ID."""
    col = get_previous_consultations_col()
    res = col.delete_one({"consultation_id": consultation_id})
    return res.deleted_count > 0
