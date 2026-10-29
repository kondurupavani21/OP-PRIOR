"""Medical Document Upload, OCR Processing, and Staff Verification Router."""
import os
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from app.schemas.medical_document import (
    DocumentResponse,
    DocumentVerifyPayload,
    DocumentReprocessPayload,
)
from app.schemas.auth import UserResponse
from app.routers.auth import get_current_user, require_doctor
from app.services.document_service import (
    save_and_process_document,
    get_patient_documents,
    get_document_by_id,
    get_document_content_preview,
    reprocess_document,
    verify_medical_document,
)

router = APIRouter(tags=["Medical Documents & OCR"])


@router.post(
    "/patients/{patient_code}/documents/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload patient medical document and execute OCR",
    description="Accepts PDF, JPEG, or PNG clinical records, performs text extraction, and identifies candidate clinical fields for staff review.",
)
@router.post(
    "/patients/{patient_code}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload patient medical document (REST endpoint)",
)
async def upload_document(
    patient_code: str,
    file: UploadFile = File(...),
    document_type: str = Form(default="PRESCRIPTION"),
    document_category: Optional[str] = Form(default=None),
    encounter_id: Optional[str] = Form(default=None),
    source_facility: Optional[str] = Form(default=None),
    source_doctor: Optional[str] = Form(default=None),
) -> DocumentResponse:
    """Intake patient document, enforce file type and size, and trigger OCR candidate extraction."""
    allowed_exts = {".pdf", ".jpg", ".jpeg", ".png", ".txt"}
    filename = file.filename or "upload.pdf"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed formats: PDF, JPEG, PNG, TXT.",
        )

    content = await file.read()
    effective_category = (document_category or document_type or "PRESCRIPTION").upper()

    try:
        return save_and_process_document(
            patient_code=patient_code,
            file_bytes=content,
            filename=filename,
            document_type=effective_category,
            encounter_id=encounter_id,
            source_facility=source_facility,
            source_doctor=source_doctor,
        )
    except ValueError as val_err:
        err_msg = str(val_err)
        if "exceed" in err_msg.lower() or "limit" in err_msg.lower() or "maximum" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document upload and processing error: {str(exc)}",
        )


@router.get(
    "/patients/{patient_code}/documents",
    response_model=List[DocumentResponse],
    summary="List patient documents",
    description="Retrieve all uploaded clinical documents, OCR status, and verification state for a patient.",
)
@router.get(
    "/documents/patient/{patient_code}",
    response_model=List[DocumentResponse],
    summary="List patient documents (alias)",
)
def list_patient_documents(patient_code: str) -> List[DocumentResponse]:
    """Retrieve document list for a patient."""
    return get_patient_documents(patient_code)


@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
    summary="Get document details & OCR fields",
)
def get_document(document_id: str) -> DocumentResponse:
    """Retrieve document details by document_id."""
    doc = get_document_by_id(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )
    return doc


@router.get(
    "/documents/{document_id}/content",
    summary="Preview extracted text and structured fields",
    description="Returns sanitized extracted text, lab values, and clinical entities without exposing raw filesystem paths.",
)
def get_document_content(document_id: str) -> Dict[str, Any]:
    """Retrieve sanitized document text content and structured candidate extractions."""
    try:
        return get_document_content_preview(document_id)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))


@router.get(
    "/documents/{document_id}/extraction",
    summary="Get structured OCR extraction entities",
)
def get_document_extraction(document_id: str) -> Dict[str, Any]:
    """Fetch structured entities (labs, medications, conditions) for a document."""
    doc = get_document_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document '{document_id}' not found.")
    return {
        "document_id": doc.document_id,
        "extracted_fields": [f.model_dump() for f in doc.extracted_fields],
        "extracted_labs": [l.model_dump() for l in doc.extracted_labs],
        "extracted_medications": [m.model_dump() for m in doc.extracted_medications],
        "has_uncertain_fields": doc.has_uncertain_fields,
        "identity_match_status": doc.identity_match_status,
    }


@router.post(
    "/documents/{document_id}/process",
    response_model=DocumentResponse,
    summary="Re-process OCR extraction",
    description="Allows staff to retry failed extraction or re-parse with force-OCR option.",
)
def reprocess_ocr(
    document_id: str,
    payload: Optional[DocumentReprocessPayload] = None,
) -> DocumentResponse:
    """Retry or re-execute OCR processing."""
    mode = payload.ocr_mode if payload else "AUTO"
    try:
        return reprocess_document(document_id=document_id, ocr_mode=mode)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.patch(
    "/documents/{document_id}/verify",
    response_model=DocumentResponse,
    summary="Human verification checkpoint for OCR fields",
    description="Authorized staff approves or rejects candidate extracted fields, committing verified items into medical_history.",
)
@router.patch(
    "/documents/{document_id}/verification",
    response_model=DocumentResponse,
    summary="Human verification checkpoint (REST alias)",
)
def verify_document_fields(
    document_id: str,
    payload: DocumentVerifyPayload,
    current_user: Optional[UserResponse] = Depends(get_current_user),
) -> DocumentResponse:
    """Verify extracted fields and commit verified clinical history."""
    try:
        reviewer_name = f"{current_user.full_name} ({current_user.role})" if current_user else "Authorized Clinician"
        return verify_medical_document(
            document_id=document_id,
            payload=payload,
            reviewer_id=reviewer_name,
        )
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Verification failed: {str(exc)}",
        )


@router.get(
    "/documents/{document_id}/download",
    summary="Download original stored document binary",
)
def download_document(document_id: str):
    """Serve the stored document file securely."""
    doc = get_document_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    from app.database.mongodb import get_medical_documents_col
    record = get_medical_documents_col().find_one({"document_id": document_id})
    if not record or not record.get("stored_file_path"):
        raise HTTPException(status_code=404, detail="Document file path not found.")

    file_path = record["stored_file_path"]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File content missing on storage volume.")

    return FileResponse(path=file_path, filename=doc.filename, media_type=doc.mime_type or "application/octet-stream")
