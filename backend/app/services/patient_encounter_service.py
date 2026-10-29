"""Domain Service for Patient Master Records and Clinical Encounters.

Implements verified identity matching, explicit physiological missingness tracking,
and synchronous emergency escalation screening against MongoDB collections.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
from app.database.mongodb import (
    get_patients_col,
    get_encounters_col,
    get_audit_events_col,
    get_medical_documents_col,
)
from app.schemas.patient_encounter import (
    PatientCreate,
    PatientUpdate,
    PatientResponse,
    EncounterCreate,
    EncounterResponse,
    utc_iso_now,
)
from app.services.emergency_screening import run_emergency_screening


def _clean_phone(phone: str) -> str:
    """Normalize phone number by stripping formatting characters."""
    return "".join(ch for ch in str(phone) if ch.isalnum() or ch == "+")


def generate_next_patient_code() -> str:
    """Generate sequential or collision-resistant patient identifier."""
    col = get_patients_col()
    count = col.count_documents({})
    candidate = f"PAT-{1001 + count}"
    # Verify no collision
    while col.find_one({"patient_code": candidate}):
        count += 1
        candidate = f"PAT-{1001 + count}"
    return candidate


def register_or_match_patient(payload: PatientCreate) -> Tuple[PatientResponse, bool]:
    """Register a new patient or return existing matched profile.
    
    Returns (PatientResponse, is_new: bool).
    """
    col = get_patients_col()
    clean_contact = _clean_phone(payload.contact)

    # 1. Identity Matching: Lookup by normalized phone number
    existing = col.find_one({"contact": clean_contact})
    if existing:
        enc_count = get_encounters_col().count_documents({"patient_code": existing["patient_code"]})
        has_docs = get_medical_documents_col().count_documents({"patient_code": existing["patient_code"]}) > 0
        resp = PatientResponse(
            patient_code=existing["patient_code"],
            full_name=existing["full_name"],
            age=existing["age"],
            gender=existing.get("gender", "Other"),
            contact=existing["contact"],
            emergency_contact=existing.get("emergency_contact"),
            blood_group=existing.get("blood_group"),
            address=existing.get("address"),
            preferred_language=existing.get("preferred_language", "English"),
            accessibility_needs=existing.get("accessibility_needs"),
            identity_verification_status=existing.get("identity_verification_status", "VERIFIED"),
            created_at=existing.get("created_at", utc_iso_now()),
            updated_at=existing.get("updated_at", utc_iso_now()),
            total_encounters=enc_count,
            has_historical_documents=has_docs,
        )
        return resp, False

    # 2. New Patient Creation
    assigned_code = payload.patient_code or generate_next_patient_code()
    now_iso = utc_iso_now()

    doc = {
        "patient_code": assigned_code,
        "full_name": payload.full_name.strip(),
        "age": payload.age,
        "gender": payload.gender,
        "contact": clean_contact,
        "emergency_contact": payload.emergency_contact,
        "blood_group": payload.blood_group,
        "address": payload.address,
        "preferred_language": payload.preferred_language,
        "accessibility_needs": payload.accessibility_needs,
        "identity_verification_status": payload.identity_verification_status,
        "created_at": now_iso,
        "updated_at": now_iso,
    }
    col.insert_one(doc)

    # Audit event
    get_audit_events_col().insert_one({
        "audit_id": f"AUD-{uuid.uuid4().hex[:10]}",
        "action": "PATIENT_REGISTERED",
        "resource_type": "patient",
        "resource_id": assigned_code,
        "timestamp": now_iso,
        "details": f"Registered new patient {payload.full_name} ({assigned_code})",
    })

    resp = PatientResponse(
        patient_code=assigned_code,
        full_name=doc["full_name"],
        age=doc["age"],
        gender=doc["gender"],
        contact=doc["contact"],
        emergency_contact=doc.get("emergency_contact"),
        blood_group=doc.get("blood_group"),
        address=doc.get("address"),
        preferred_language=doc.get("preferred_language", "English"),
        accessibility_needs=doc.get("accessibility_needs"),
        identity_verification_status=doc.get("identity_verification_status", "VERIFIED"),
        created_at=now_iso,
        updated_at=now_iso,
        total_encounters=0,
        has_historical_documents=False,
    )
    return resp, True


def get_patient_by_code(patient_code: str) -> Optional[PatientResponse]:
    """Retrieve patient record by patient_code."""
    col = get_patients_col()
    doc = col.find_one({"patient_code": patient_code})
    if not doc:
        return None

    enc_count = get_encounters_col().count_documents({"patient_code": patient_code})
    has_docs = get_medical_documents_col().count_documents({"patient_code": patient_code}) > 0

    return PatientResponse(
        patient_code=doc["patient_code"],
        full_name=doc["full_name"],
        age=doc["age"],
        gender=doc.get("gender", "Other"),
        contact=doc["contact"],
        emergency_contact=doc.get("emergency_contact"),
        blood_group=doc.get("blood_group"),
        address=doc.get("address"),
        preferred_language=doc.get("preferred_language", "English"),
        accessibility_needs=doc.get("accessibility_needs"),
        identity_verification_status=doc.get("identity_verification_status", "VERIFIED"),
        created_at=doc.get("created_at", utc_iso_now()),
        updated_at=doc.get("updated_at", utc_iso_now()),
        total_encounters=enc_count,
        has_historical_documents=has_docs,
    )


def search_patients(query: Optional[str] = None, skip: int = 0, limit: int = 50) -> List[PatientResponse]:
    """Search patients by patient_code, name, or phone."""
    col = get_patients_col()
    filter_q: Dict[str, Any] = {}
    if query:
        q = query.strip()
        filter_q = {
            "$or": [
                {"patient_code": {"$regex": q, "$options": "i"}},
                {"full_name": {"$regex": q, "$options": "i"}},
                {"contact": {"$regex": q, "$options": "i"}},
            ]
        }

    cursor = col.find(filter_q).skip(skip).limit(limit)
    results: List[PatientResponse] = []
    for doc in cursor:
        enc_count = get_encounters_col().count_documents({"patient_code": doc["patient_code"]})
        has_docs = get_medical_documents_col().count_documents({"patient_code": doc["patient_code"]}) > 0
        results.append(PatientResponse(
            patient_code=doc["patient_code"],
            full_name=doc["full_name"],
            age=doc["age"],
            gender=doc.get("gender", "Other"),
            contact=doc["contact"],
            emergency_contact=doc.get("emergency_contact"),
            blood_group=doc.get("blood_group"),
            address=doc.get("address"),
            preferred_language=doc.get("preferred_language", "English"),
            accessibility_needs=doc.get("accessibility_needs"),
            identity_verification_status=doc.get("identity_verification_status", "VERIFIED"),
            created_at=doc.get("created_at", utc_iso_now()),
            updated_at=doc.get("updated_at", utc_iso_now()),
            total_encounters=enc_count,
            has_historical_documents=has_docs,
        ))
    return results


def create_encounter(payload: EncounterCreate) -> EncounterResponse:
    """Create a new clinical encounter with emergency screening and missingness tracking."""
    # 1. Verify Patient
    patient = get_patient_by_code(payload.patient_code)
    if not patient:
        raise ValueError(f"Patient with code '{payload.patient_code}' not found.")

    vitals_dict = payload.vitals.model_dump(exclude_none=False)

    # 2. Build explicit missingness indicators
    missingness = {
        "temperature_missing": vitals_dict.get("temperature") is None,
        "heart_rate_missing": vitals_dict.get("heart_rate") is None,
        "respiratory_rate_missing": vitals_dict.get("respiratory_rate") is None,
        "systolic_bp_missing": vitals_dict.get("systolic_bp") is None,
        "diastolic_bp_missing": vitals_dict.get("diastolic_bp") is None,
        "spo2_missing": vitals_dict.get("spo2") is None,
        "blood_sugar_missing": vitals_dict.get("blood_sugar") is None,
        "pain_score_missing": vitals_dict.get("pain_score") is None or vitals_dict.get("pain_score") == -1,
    }

    # 3. Synchronous Emergency Screening
    screening = run_emergency_screening(
        vitals=vitals_dict,
        symptoms=payload.symptoms,
        chief_complaint=payload.chief_complaint,
        mental_status=payload.mental_status,
    )

    now_iso = utc_iso_now()
    enc_id = f"ENC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    status = "ESCALATED_EMERGENCY" if screening.is_emergency else "WAITING"

    encounter_doc = {
        "encounter_id": enc_id,
        "patient_code": payload.patient_code,
        "patient_name": patient.full_name,
        "department": payload.department,
        "arrival_time": now_iso,
        "visit_type": payload.visit_type,
        "chief_complaint": payload.chief_complaint,
        "complaint_category": payload.complaint_category or "General",
        "symptom_duration": payload.symptom_duration or "1 day",
        "symptoms": payload.symptoms,
        "vitals": vitals_dict,
        "missingness_indicators": missingness,
        "measurement_source": payload.measurement_source,
        "mental_status": payload.mental_status,
        "is_emergency": screening.is_emergency,
        "escalation_level": screening.escalation_level,
        "escalation_reasons": screening.escalation_reasons,
        "action_required": screening.action_required,
        "status": status,
        "created_at": now_iso,
    }

    get_encounters_col().insert_one(encounter_doc)

    # Audit event
    get_audit_events_col().insert_one({
        "audit_id": f"AUD-{uuid.uuid4().hex[:10]}",
        "action": "ENCOUNTER_CREATED",
        "resource_type": "encounter",
        "resource_id": enc_id,
        "timestamp": now_iso,
        "details": f"Encounter created for {patient.full_name} ({payload.patient_code}), emergency={screening.is_emergency}",
    })

    return EncounterResponse(
        encounter_id=enc_id,
        patient_code=payload.patient_code,
        patient_name=patient.full_name,
        department=payload.department,
        arrival_time=now_iso,
        visit_type=payload.visit_type,
        chief_complaint=payload.chief_complaint,
        complaint_category=encounter_doc["complaint_category"],
        symptom_duration=encounter_doc["symptom_duration"],
        symptoms=payload.symptoms,
        vitals=vitals_dict,
        missingness_indicators=missingness,
        is_emergency=screening.is_emergency,
        escalation_level=screening.escalation_level,
        escalation_reasons=screening.escalation_reasons,
        action_required=screening.action_required,
        status=status,
        created_at=now_iso,
    )


def get_encounter_by_id(encounter_id: str) -> Optional[EncounterResponse]:
    """Retrieve encounter by ID."""
    doc = get_encounters_col().find_one({"encounter_id": encounter_id})
    if not doc:
        return None
    return EncounterResponse(
        encounter_id=doc["encounter_id"],
        patient_code=doc["patient_code"],
        patient_name=doc.get("patient_name", "Unknown"),
        department=doc.get("department", "General Medicine"),
        arrival_time=doc.get("arrival_time", utc_iso_now()),
        visit_type=doc.get("visit_type", "NEW"),
        chief_complaint=doc.get("chief_complaint", ""),
        complaint_category=doc.get("complaint_category", "General"),
        symptom_duration=doc.get("symptom_duration", ""),
        symptoms=doc.get("symptoms", []),
        vitals=doc.get("vitals", {}),
        missingness_indicators=doc.get("missingness_indicators", {}),
        is_emergency=doc.get("is_emergency", False),
        escalation_level=doc.get("escalation_level", "STANDARD"),
        escalation_reasons=doc.get("escalation_reasons", []),
        action_required=doc.get("action_required", "Standard queue pathway."),
        status=doc.get("status", "WAITING"),
        created_at=doc.get("created_at", utc_iso_now()),
    )


def get_encounters_by_patient(patient_code: str) -> List[EncounterResponse]:
    """Retrieve all historical encounters for a given patient."""
    cursor = get_encounters_col().find({"patient_code": patient_code}).sort("arrival_time", -1)
    results: List[EncounterResponse] = []
    for doc in cursor:
        results.append(EncounterResponse(
            encounter_id=doc["encounter_id"],
            patient_code=doc["patient_code"],
            patient_name=doc.get("patient_name", "Unknown"),
            department=doc.get("department", "General Medicine"),
            arrival_time=doc.get("arrival_time", utc_iso_now()),
            visit_type=doc.get("visit_type", "NEW"),
            chief_complaint=doc.get("chief_complaint", ""),
            complaint_category=doc.get("complaint_category", "General"),
            symptom_duration=doc.get("symptom_duration", ""),
            symptoms=doc.get("symptoms", []),
            vitals=doc.get("vitals", {}),
            missingness_indicators=doc.get("missingness_indicators", {}),
            is_emergency=doc.get("is_emergency", False),
            escalation_level=doc.get("escalation_level", "STANDARD"),
            escalation_reasons=doc.get("escalation_reasons", []),
            action_required=doc.get("action_required", "Standard queue pathway."),
            status=doc.get("status", "WAITING"),
            created_at=doc.get("created_at", utc_iso_now()),
        ))
    return results
