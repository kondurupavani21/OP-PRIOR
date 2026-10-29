"""Service managing Verified Medical History and Longitudinal Clinical Facts."""
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from app.database.mongodb import (
    get_medical_history_col,
    get_medical_documents_col,
    get_audit_events_col,
    get_patients_col,
)
from app.schemas.medical_history import (
    MedicalHistoryItem,
    MedicalHistoryCreate,
    PatientHistorySummaryResponse,
)


def utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_patient_history_summary(patient_code: str) -> PatientHistorySummaryResponse:
    """Retrieve aggregated verified longitudinal history for a patient."""
    hist_col = get_medical_history_col()
    doc_col = get_medical_documents_col()

    cursor = hist_col.find({"patient_code": patient_code, "verification_status": "VERIFIED"}).sort("verified_at", -1)
    items: List[MedicalHistoryItem] = []
    conditions: List[str] = []
    medications: List[str] = []
    allergies: List[str] = []

    for doc in cursor:
        item = MedicalHistoryItem(
            history_id=doc["history_id"],
            patient_code=doc["patient_code"],
            record_type=doc.get("record_type", "CONDITION"),
            condition_name=doc.get("condition_name"),
            medication_name=doc.get("medication_name"),
            allergen=doc.get("allergen"),
            diagnosed_date=doc.get("diagnosed_date"),
            status=doc.get("status", "ACTIVE"),
            source_type=doc.get("source_type", "VERIFIED_OCR_DOCUMENT"),
            source_document_id=doc.get("source_document_id"),
            verification_status=doc.get("verification_status", "VERIFIED"),
            verifier_id=doc.get("verifier_id"),
            verified_at=doc.get("verified_at"),
        )
        items.append(item)

        if item.record_type == "CONDITION" and item.condition_name and item.condition_name not in conditions:
            conditions.append(item.condition_name)
        elif item.record_type == "MEDICATION" and item.medication_name and item.medication_name not in medications:
            medications.append(item.medication_name)
        elif item.record_type == "ALLERGY" and item.allergen and item.allergen not in allergies:
            allergies.append(item.allergen)

    # Check unverified documents count
    unverified_count = doc_col.count_documents({
        "patient_code": patient_code,
        "verification_status": "PENDING_REVIEW",
    })

    return PatientHistorySummaryResponse(
        patient_code=patient_code,
        verified_conditions=conditions,
        active_medications=medications,
        known_allergies=allergies,
        history_items=items,
        has_unverified_documents=unverified_count > 0,
        unverified_document_count=unverified_count,
    )


def add_manual_history_item(
    patient_code: str,
    payload: MedicalHistoryCreate,
    verifier_id: str,
) -> MedicalHistoryItem:
    """Manually add a verified clinical history entry by clinician."""
    patient = get_patients_col().find_one({"patient_code": patient_code})
    if not patient:
        raise ValueError(f"Patient with code '{patient_code}' not found.")

    hist_col = get_medical_history_col()
    now_iso = utc_iso_now()
    hist_id = f"HIST-{uuid.uuid4().hex[:8].upper()}"

    doc = {
        "history_id": hist_id,
        "patient_code": patient_code,
        "record_type": payload.record_type,
        "condition_name": payload.name if payload.record_type == "CONDITION" else None,
        "medication_name": payload.name if payload.record_type == "MEDICATION" else None,
        "allergen": payload.name if payload.record_type == "ALLERGY" else None,
        "diagnosed_date": payload.diagnosed_date or now_iso[:10],
        "status": payload.status,
        "source_type": "CLINICIAN_ENTERED",
        "source_document_id": None,
        "verification_status": "VERIFIED",
        "verifier_id": verifier_id,
        "verified_at": now_iso,
    }

    hist_col.insert_one(doc)

    get_audit_events_col().insert_one({
        "audit_id": f"AUD-{uuid.uuid4().hex[:10]}",
        "action": "HISTORY_ITEM_ADDED",
        "user_id": verifier_id,
        "resource_type": "medical_history",
        "resource_id": hist_id,
        "timestamp": now_iso,
        "details": f"Added {payload.record_type} '{payload.name}' for patient {patient_code}",
    })

    return MedicalHistoryItem(**doc)
