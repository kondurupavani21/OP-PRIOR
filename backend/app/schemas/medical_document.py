"""Pydantic v2 schemas for Medical Document Upload, OCR, Structured Extraction, and Verification."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ExtractedFieldItem(BaseModel):
    """An individual field candidate extracted via OCR/Parser."""
    field_name: str = Field(..., description="E.g., diagnosis, medication, allergy, document_date, clinic_name, doctor_name")
    extracted_value: str
    corrected_value: Optional[str] = None
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    is_uncertain: bool = Field(default=False, description="Flagged true if illegible, conflicting, or low confidence")
    status: str = Field(default="UNVERIFIED", description="UNVERIFIED, VERIFIED, or REJECTED")


class ExtractedLabItem(BaseModel):
    """Structured laboratory result from report."""
    test_name: str
    result_value: str
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    is_abnormal: bool = False
    flag: Optional[str] = None  # HIGH, LOW, CRITICAL, ABNORMAL
    confidence: float = 0.85
    is_uncertain: bool = False


class ExtractedMedicationItem(BaseModel):
    """Structured medication extracted from prescription or note."""
    medicine_name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    instructions: Optional[str] = None
    confidence: float = 0.85
    is_uncertain: bool = False


class DocumentResponse(BaseModel):
    """Metadata and OCR extraction state for an uploaded medical document."""
    document_id: str = Field(..., description="Unique identifier, e.g. DOC-20261026-A1B2")
    patient_code: str
    encounter_id: Optional[str] = None
    filename: str
    file_type: str
    document_category: str = Field(
        default="PRESCRIPTION",
        description="PRESCRIPTION, LAB_REPORT, RADIOLOGY_REPORT, DISCHARGE_SUMMARY, CONSULTATION_NOTE, EMR_EXPORT, OTHER",
    )
    document_type: str = Field(default="PRESCRIPTION", description="Alias for document_category")
    document_date: Optional[str] = None
    source_facility: Optional[str] = None
    source_doctor: Optional[str] = None
    upload_timestamp: str
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    ocr_engine: str = Field(default="DIRECT_PDF_EXTRACTION_AND_OCR")
    ocr_processing_status: str = Field(default="COMPLETED", description="COMPLETED, PROCESSING, FAILED")
    identity_match_status: str = Field(
        default="MATCHED",
        description="MATCHED, UNCERTAIN, or MISMATCH (requires human confirmation)",
    )
    identity_match_details: Optional[str] = None
    detected_patient_name: Optional[str] = None
    has_uncertain_fields: bool = False
    error_message: Optional[str] = None
    extracted_text: str = ""
    extracted_fields: List[ExtractedFieldItem] = Field(default_factory=list)
    extracted_labs: List[ExtractedLabItem] = Field(default_factory=list)
    extracted_medications: List[ExtractedMedicationItem] = Field(default_factory=list)
    verification_status: str = Field(default="PENDING_REVIEW", description="PENDING_REVIEW, NEEDS_REVIEW, VERIFIED, REJECTED")
    reviewer_id: Optional[str] = None
    reviewed_at: Optional[str] = None
    reviewer_notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentVerifyPayload(BaseModel):
    """Staff verification submission for OCR fields."""
    verification_status: str = Field(..., description="'VERIFIED' to confirm fields or 'REJECTED' to discard")
    reviewer_notes: Optional[str] = Field(default=None)
    verified_conditions: Optional[List[str]] = Field(default_factory=list, description="Confirmed chronic conditions to commit to history")
    verified_medications: Optional[List[str]] = Field(default_factory=list, description="Confirmed active medications")
    verified_allergies: Optional[List[str]] = Field(default_factory=list, description="Confirmed clinical allergies")
    confirm_patient_identity: Optional[bool] = Field(default=True, description="Explicit human confirmation that document belongs to patient")
    field_corrections: Optional[Dict[str, str]] = Field(default=None, description="Corrected values for extracted fields")


class DocumentReprocessPayload(BaseModel):
    """Trigger re-processing or retry of OCR extraction."""
    ocr_mode: Optional[str] = Field(default="AUTO", description="AUTO, FORCE_OCR, FORCE_TEXT")
