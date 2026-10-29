"""Pydantic schemas for Verified Medical History & Longitudinal Records."""
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class MedicalHistoryItem(BaseModel):
    """An individual verified clinical fact with source provenance."""
    history_id: str
    patient_code: str
    record_type: str = Field(..., description="CONDITION, MEDICATION, ALLERGY, or DIAGNOSIS")
    condition_name: Optional[str] = None
    medication_name: Optional[str] = None
    allergen: Optional[str] = None
    diagnosed_date: Optional[str] = None
    status: str = Field(default="ACTIVE", description="ACTIVE or RESOLVED")
    source_type: str = Field(default="VERIFIED_OCR_DOCUMENT", description="VERIFIED_OCR_DOCUMENT, CLINICIAN_ENTERED, PREVIOUS_ENCOUNTER")
    source_document_id: Optional[str] = None
    verification_status: str = Field(default="VERIFIED")
    verifier_id: Optional[str] = None
    verified_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MedicalHistoryCreate(BaseModel):
    """Payload for clinician to manually record a verified condition or allergy."""
    record_type: str = Field(default="CONDITION", description="CONDITION, MEDICATION, or ALLERGY")
    name: str = Field(..., min_length=2, description="Name of condition, medication, or allergen")
    diagnosed_date: Optional[str] = None
    status: str = Field(default="ACTIVE")


class PatientHistorySummaryResponse(BaseModel):
    """Aggregated verified clinical history with source grounding."""
    patient_code: str
    verified_conditions: List[str] = Field(default_factory=list)
    active_medications: List[str] = Field(default_factory=list)
    known_allergies: List[str] = Field(default_factory=list)
    history_items: List[MedicalHistoryItem] = Field(default_factory=list)
    has_unverified_documents: bool = False
    unverified_document_count: int = 0
