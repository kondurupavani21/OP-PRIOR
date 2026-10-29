"""Service managing medical document uploads, OCR execution, patient matching, and staff verification."""
import os
import uuid
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from app.core.config import settings
from app.database.mongodb import (
    get_medical_documents_col,
    get_medical_history_col,
    get_audit_events_col,
    get_patients_col,
    get_document_extractions_col,
)
from app.schemas.medical_document import (
    DocumentResponse,
    DocumentVerifyPayload,
    ExtractedFieldItem,
    ExtractedLabItem,
    ExtractedMedicationItem,
)
from app.services.ocr_service import extract_clinical_text, parse_clinical_entities

UPLOAD_BASE = Path(__file__).resolve().parent.parent.parent / settings.UPLOAD_DIR


def utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _detect_mime_type(file_bytes: bytes, filename: str) -> str:
    """Identify mime-type using magic bytes inspection and file extension."""
    if file_bytes.startswith(b"%PDF-"):
        return "application/pdf"
    elif file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    elif file_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".txt":
        return "text/plain"
    elif ext == ".pdf":
        return "application/pdf"
    elif ext in [".jpg", ".jpeg"]:
        return "image/jpeg"
    elif ext == ".png":
        return "image/png"
    return "application/octet-stream"


def _check_patient_identity_match(
    extracted_fields: List[ExtractedFieldItem],
    patient: Dict[str, Any],
) -> Tuple[str, Optional[str], Optional[str]]:
    """Compare extracted identity fields with registered patient profile."""
    registered_name = (patient.get("full_name") or "").strip().lower()
    registered_age = patient.get("age")

    detected_name = None
    detected_age = None
    for field in extracted_fields:
        if field.field_name == "patient_name":
            detected_name = field.extracted_value.strip()
        elif field.field_name == "patient_age":
            try:
                detected_age = int(field.extracted_value.strip())
            except Exception:
                pass

    if not detected_name:
        # No printed name detected; document may be an anonymous lab/prescription scan
        return "UNCERTAIN", "No patient name detected on source document. Requires staff manual identity confirmation.", None

    det_lower = detected_name.lower()
    # Check token overlap
    reg_tokens = set(re_word for re_word in registered_name.split() if len(re_word) > 1)
    det_tokens = set(re_word for re_word in det_lower.split() if len(re_word) > 1)
    overlap = reg_tokens.intersection(det_tokens)

    if overlap:
        # Name tokens match
        return "MATCHED", f"Identity matched with registered patient '{patient.get('full_name')}'.", detected_name

    # Significant mismatch
    return (
        "MISMATCH",
        f"Potential identity mismatch: Document contains patient name '{detected_name}' which does not match registered name '{patient.get('full_name')}'.",
        detected_name,
    )


def save_and_process_document(
    patient_code: str,
    file_bytes: bytes,
    filename: str,
    document_type: str = "PRESCRIPTION",
    encounter_id: Optional[str] = None,
    source_facility: Optional[str] = None,
    source_doctor: Optional[str] = None,
) -> DocumentResponse:
    """Save raw document securely, execute OCR/extraction, check identity matching, and record audit event."""
    # 1. Ensure patient exists
    patient = get_patients_col().find_one({"patient_code": patient_code})
    if not patient:
        raise ValueError(f"Patient with code '{patient_code}' not found.")

    # 2. File size validation
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise ValueError(f"File exceeds maximum allowed upload size of {settings.MAX_UPLOAD_SIZE_MB} MB.")

    # 3. MIME type inspection
    mime_type = _detect_mime_type(file_bytes, filename)
    allowed_mimes = {"application/pdf", "image/png", "image/jpeg", "text/plain"}
    if mime_type not in allowed_mimes:
        raise ValueError(f"Unsupported file format '{mime_type}'. Supported formats: PDF, PNG, JPEG, TXT.")

    # 4. Safe server-side storage filename
    patient_dir = UPLOAD_BASE / patient_code
    patient_dir.mkdir(parents=True, exist_ok=True)

    file_ext = os.path.splitext(filename)[1].lower() or ".bin"
    file_hash = hashlib.sha256(file_bytes).hexdigest()[:12]
    clean_storage_filename = f"{uuid.uuid4().hex[:8]}_{file_hash}{file_ext}"
    file_path = str(patient_dir / clean_storage_filename)

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    # 5. Execute OCR / Direct Text Extraction
    raw_text, ocr_engine, meta = extract_clinical_text(file_path, filename)
    extracted_fields, extracted_labs, extracted_meds = parse_clinical_entities(raw_text)

    # 6. Patient Identity Matching Check
    id_status, id_details, det_name = _check_patient_identity_match(extracted_fields, patient)

    # 7. Document metadata extraction
    doc_date = None
    fac_name = source_facility
    doc_name = source_doctor
    has_uncertain = any(f.is_uncertain for f in extracted_fields) or any(m.is_uncertain for m in extracted_meds)

    for field in extracted_fields:
        if field.field_name == "document_date" and not doc_date:
            doc_date = field.extracted_value
        elif field.field_name == "facility_name" and not fac_name:
            fac_name = field.extracted_value
        elif field.field_name == "doctor_name" and not doc_name:
            doc_name = field.extracted_value

    # If identity is uncertain or mismatched, require manual verification
    initial_verif_status = "NEEDS_REVIEW" if id_status in ["UNCERTAIN", "MISMATCH"] else "PENDING_REVIEW"

    doc_id = f"DOC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    now_iso = utc_iso_now()

    doc_record = {
        "document_id": doc_id,
        "patient_code": patient_code,
        "encounter_id": encounter_id,
        "filename": filename,
        "stored_file_path": file_path,
        "file_type": file_ext,
        "mime_type": mime_type,
        "file_size": len(file_bytes),
        "document_category": document_type.upper(),
        "document_type": document_type.upper(),
        "document_date": doc_date,
        "source_facility": fac_name,
        "source_doctor": doc_name,
        "upload_timestamp": now_iso,
        "ocr_engine": ocr_engine,
        "ocr_processing_status": "COMPLETED",
        "identity_match_status": id_status,
        "identity_match_details": id_details,
        "detected_patient_name": det_name,
        "has_uncertain_fields": has_uncertain,
        "extracted_text": raw_text,
        "extracted_fields": [f.model_dump() for f in extracted_fields],
        "extracted_labs": [l.model_dump() for l in extracted_labs],
        "extracted_medications": [m.model_dump() for m in extracted_meds],
        "verification_status": initial_verif_status,
        "reviewer_id": None,
        "reviewed_at": None,
        "reviewer_notes": None,
    }

    get_medical_documents_col().insert_one(doc_record)

    # Also persist to dedicated document_extractions collection
    get_document_extractions_col().insert_one({
        "document_id": doc_id,
        "patient_code": patient_code,
        "extracted_text": raw_text,
        "extracted_fields": [f.model_dump() for f in extracted_fields],
        "extracted_labs": [l.model_dump() for l in extracted_labs],
        "extracted_medications": [m.model_dump() for m in extracted_meds],
        "ocr_engine": ocr_engine,
        "created_at": now_iso,
    })

    # Audit event logging
    get_audit_events_col().insert_one({
        "audit_id": f"AUD-{uuid.uuid4().hex[:10]}",
        "action": "DOCUMENT_UPLOADED",
        "resource_type": "medical_document",
        "resource_id": doc_id,
        "timestamp": now_iso,
        "details": f"Uploaded document '{filename}' for patient {patient_code}, category={document_type}, match={id_status}",
    })

    return DocumentResponse(
        document_id=doc_id,
        patient_code=patient_code,
        encounter_id=encounter_id,
        filename=filename,
        file_type=file_ext,
        mime_type=mime_type,
        file_size=len(file_bytes),
        document_category=document_type.upper(),
        document_type=document_type.upper(),
        document_date=doc_date,
        source_facility=fac_name,
        source_doctor=doc_name,
        upload_timestamp=now_iso,
        ocr_engine=ocr_engine,
        ocr_processing_status="COMPLETED",
        identity_match_status=id_status,
        identity_match_details=id_details,
        detected_patient_name=det_name,
        has_uncertain_fields=has_uncertain,
        extracted_text=raw_text,
        extracted_fields=extracted_fields,
        extracted_labs=extracted_labs,
        extracted_medications=extracted_meds,
        verification_status=initial_verif_status,
    )


def get_patient_documents(patient_code: str) -> List[DocumentResponse]:
    """Retrieve all uploaded documents for a patient."""
    col = get_medical_documents_col()
    cursor = col.find({"patient_code": patient_code}).sort("upload_timestamp", -1)
    results: List[DocumentResponse] = []
    for doc in cursor:
        results.append(_to_document_response(doc))
    return results


def get_document_by_id(document_id: str) -> Optional[DocumentResponse]:
    """Retrieve document details by document_id."""
    col = get_medical_documents_col()
    doc = col.find_one({"document_id": document_id})
    if not doc:
        return None
    return _to_document_response(doc)


def get_document_content_preview(document_id: str) -> Dict[str, Any]:
    """Return sanitized extracted text, lab values, and structured fields for doctor inspection."""
    doc = get_medical_documents_col().find_one({"document_id": document_id})
    if not doc:
        raise ValueError(f"Document with ID '{document_id}' not found.")

    return {
        "document_id": doc["document_id"],
        "filename": doc.get("filename", "unknown"),
        "document_category": doc.get("document_category", "PRESCRIPTION"),
        "document_date": doc.get("document_date"),
        "source_facility": doc.get("source_facility"),
        "ocr_engine": doc.get("ocr_engine"),
        "identity_match_status": doc.get("identity_match_status", "MATCHED"),
        "verification_status": doc.get("verification_status", "PENDING_REVIEW"),
        "extracted_text": doc.get("extracted_text", ""),
        "extracted_fields": doc.get("extracted_fields", []),
        "extracted_labs": doc.get("extracted_labs", []),
        "extracted_medications": doc.get("extracted_medications", []),
    }


def reprocess_document(document_id: str, ocr_mode: str = "AUTO") -> DocumentResponse:
    """Re-run OCR extraction on an existing stored document."""
    col = get_medical_documents_col()
    doc = col.find_one({"document_id": document_id})
    if not doc:
        raise ValueError(f"Document with ID '{document_id}' not found.")

    file_path = doc.get("stored_file_path")
    if not file_path or not os.path.exists(file_path):
        raise ValueError(f"Stored document file content missing for '{document_id}'.")

    raw_text, ocr_engine, _ = extract_clinical_text(file_path, doc.get("filename", "doc"))
    extracted_fields, extracted_labs, extracted_meds = parse_clinical_entities(raw_text)

    patient = get_patients_col().find_one({"patient_code": doc["patient_code"]}) or {}
    id_status, id_details, det_name = _check_patient_identity_match(extracted_fields, patient)

    update_fields = {
        "extracted_text": raw_text,
        "ocr_engine": f"{ocr_engine} (Reprocessed)",
        "ocr_processing_status": "COMPLETED",
        "identity_match_status": id_status,
        "identity_match_details": id_details,
        "detected_patient_name": det_name,
        "extracted_fields": [f.model_dump() for f in extracted_fields],
        "extracted_labs": [l.model_dump() for l in extracted_labs],
        "extracted_medications": [m.model_dump() for m in extracted_meds],
        "updated_at": utc_iso_now(),
    }

    col.update_one({"document_id": document_id}, {"$set": update_fields})
    updated = col.find_one({"document_id": document_id})
    return _to_document_response(updated)


def verify_medical_document(
    document_id: str,
    payload: DocumentVerifyPayload,
    reviewer_id: str,
) -> DocumentResponse:
    """Authorized review checkpoint: commits verified clinical entities into medical_history collection."""
    doc_col = get_medical_documents_col()
    doc = doc_col.find_one({"document_id": document_id})
    if not doc:
        raise ValueError(f"Document with ID '{document_id}' not found.")

    now_iso = utc_iso_now()
    patient_code = doc["patient_code"]

    if payload.verification_status == "VERIFIED":
        hist_col = get_medical_history_col()

        # 1. Commit Verified Chronic Conditions
        for cond in (payload.verified_conditions or []):
            if not hist_col.find_one({"patient_code": patient_code, "condition_name": cond}):
                hist_col.insert_one({
                    "history_id": f"HIST-{uuid.uuid4().hex[:8].upper()}",
                    "patient_code": patient_code,
                    "condition_name": cond,
                    "record_type": "CONDITION",
                    "diagnosed_date": doc.get("document_date") or now_iso[:10],
                    "status": "ACTIVE",
                    "source_type": "VERIFIED_OCR_DOCUMENT",
                    "source_document_id": document_id,
                    "verification_status": "VERIFIED",
                    "verifier_id": reviewer_id,
                    "verified_at": now_iso,
                })

        # 2. Commit Verified Active Medications
        for med in (payload.verified_medications or []):
            if not hist_col.find_one({"patient_code": patient_code, "medication_name": med}):
                hist_col.insert_one({
                    "history_id": f"HIST-{uuid.uuid4().hex[:8].upper()}",
                    "patient_code": patient_code,
                    "medication_name": med,
                    "record_type": "MEDICATION",
                    "status": "ACTIVE",
                    "source_type": "VERIFIED_OCR_DOCUMENT",
                    "source_document_id": document_id,
                    "verification_status": "VERIFIED",
                    "verifier_id": reviewer_id,
                    "verified_at": now_iso,
                })

        # 3. Commit Verified Allergies
        for alg in (payload.verified_allergies or []):
            if not hist_col.find_one({"patient_code": patient_code, "allergen": alg}):
                hist_col.insert_one({
                    "history_id": f"HIST-{uuid.uuid4().hex[:8].upper()}",
                    "patient_code": patient_code,
                    "allergen": alg,
                    "record_type": "ALLERGY",
                    "status": "ACTIVE",
                    "source_type": "VERIFIED_OCR_DOCUMENT",
                    "source_document_id": document_id,
                    "verification_status": "VERIFIED",
                    "verifier_id": reviewer_id,
                    "verified_at": now_iso,
                })

    # Update document record state
    update_data = {
        "verification_status": payload.verification_status,
        "reviewer_id": reviewer_id,
        "reviewed_at": now_iso,
        "reviewer_notes": payload.reviewer_notes,
    }
    if payload.confirm_patient_identity:
        update_data["identity_match_status"] = "MATCHED"

    doc_col.update_one({"document_id": document_id}, {"$set": update_data})

    # Audit event logging
    get_audit_events_col().insert_one({
        "audit_id": f"AUD-{uuid.uuid4().hex[:10]}",
        "action": "DOCUMENT_VERIFIED" if payload.verification_status == "VERIFIED" else "DOCUMENT_REJECTED",
        "user_id": reviewer_id,
        "resource_type": "medical_document",
        "resource_id": document_id,
        "timestamp": now_iso,
        "details": f"Document {document_id} marked as {payload.verification_status} by {reviewer_id}",
    })

    return get_document_by_id(document_id)


def _to_document_response(doc: Dict[str, Any]) -> DocumentResponse:
    """Helper converting MongoDB document dict to Pydantic DocumentResponse."""
    return DocumentResponse(
        document_id=doc["document_id"],
        patient_code=doc["patient_code"],
        encounter_id=doc.get("encounter_id"),
        filename=doc.get("filename", "unknown"),
        file_type=doc.get("file_type", ""),
        mime_type=doc.get("mime_type"),
        file_size=doc.get("file_size"),
        document_category=doc.get("document_category", doc.get("document_type", "PRESCRIPTION")),
        document_type=doc.get("document_type", "PRESCRIPTION"),
        document_date=doc.get("document_date"),
        source_facility=doc.get("source_facility"),
        source_doctor=doc.get("source_doctor"),
        upload_timestamp=doc.get("upload_timestamp", utc_iso_now()),
        ocr_engine=doc.get("ocr_engine", "OCR"),
        ocr_processing_status=doc.get("ocr_processing_status", "COMPLETED"),
        identity_match_status=doc.get("identity_match_status", "MATCHED"),
        identity_match_details=doc.get("identity_match_details"),
        detected_patient_name=doc.get("detected_patient_name"),
        has_uncertain_fields=doc.get("has_uncertain_fields", False),
        error_message=doc.get("error_message"),
        extracted_text=doc.get("extracted_text", ""),
        extracted_fields=[ExtractedFieldItem(**f) for f in doc.get("extracted_fields", [])],
        extracted_labs=[ExtractedLabItem(**l) for l in doc.get("extracted_labs", [])],
        extracted_medications=[ExtractedMedicationItem(**m) for m in doc.get("extracted_medications", [])],
        verification_status=doc.get("verification_status", "PENDING_REVIEW"),
        reviewer_id=doc.get("reviewer_id"),
        reviewed_at=doc.get("reviewed_at"),
        reviewer_notes=doc.get("reviewer_notes"),
    )
