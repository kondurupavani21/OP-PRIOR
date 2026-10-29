"""Pydantic v2 schemas for Patient Profiles, Encounters, and Intake Vitals."""
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


def utc_iso_now() -> str:
    """Return timezone-aware ISO string for current UTC time."""
    return datetime.now(timezone.utc).isoformat()


# =========================================================================
# Patient Schemas
# =========================================================================

class PatientBase(BaseModel):
    """Core demographic attributes of a patient."""
    full_name: str = Field(..., min_length=1, max_length=255, description="Full legal or presenting name")
    age: int = Field(..., ge=0, le=130, description="Age in years")
    gender: str = Field(default="Other", description="Male, Female, or Other")
    contact: str = Field(..., min_length=7, max_length=32, description="Primary contact phone number")
    emergency_contact: Optional[str] = Field(default=None, description="Emergency contact phone or name")
    blood_group: Optional[str] = Field(default=None, description="E.g., A+, O-, B+")
    address: Optional[str] = Field(default=None, description="Residential address or locality")
    preferred_language: str = Field(default="English", description="Preferred spoken/written language")
    accessibility_needs: Optional[str] = Field(default=None, description="Wheelchair, hearing impaired, etc.")
    identity_verification_status: str = Field(
        default="VERIFIED",
        description="VERIFIED, PENDING_REVIEW, or UNCONFIRMED",
    )


class PatientCreate(PatientBase):
    """Payload for registering a new patient."""
    patient_code: Optional[str] = Field(default=None, description="Optional custom code or auto-generated")
    initial_symptoms: Optional[List[str]] = Field(default_factory=list)
    initial_vitals: Optional[Dict[str, Any]] = Field(default=None)


class PatientUpdate(BaseModel):
    """Editable patient profile fields."""
    full_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    contact: Optional[str] = None
    emergency_contact: Optional[str] = None
    blood_group: Optional[str] = None
    address: Optional[str] = None
    preferred_language: Optional[str] = None
    accessibility_needs: Optional[str] = None
    identity_verification_status: Optional[str] = None


class PatientResponse(PatientBase):
    """Complete patient master profile returned to API clients."""
    patient_code: str = Field(..., description="Unique alphanumeric identifier, e.g. PAT-1001")
    created_at: str = Field(default_factory=utc_iso_now)
    updated_at: str = Field(default_factory=utc_iso_now)
    total_encounters: int = Field(default=0)
    has_historical_documents: bool = Field(default=False)


# =========================================================================
# Encounter & Intake Vitals Schemas
# =========================================================================

class VitalSignsInput(BaseModel):
    """Intake physiological measurements with explicit missingness support."""
    temperature: Optional[float] = Field(default=None, description="Temperature in Fahrenheit (e.g. 98.6)")
    heart_rate: Optional[int] = Field(default=None, ge=20, le=300, description="Pulse in beats per minute")
    respiratory_rate: Optional[int] = Field(default=None, ge=5, le=80, description="Breaths per minute")
    systolic_bp: Optional[int] = Field(default=None, ge=40, le=280, description="Systolic blood pressure mmHg")
    diastolic_bp: Optional[int] = Field(default=None, ge=20, le=180, description="Diastolic blood pressure mmHg")
    spo2: Optional[float] = Field(default=None, ge=30.0, le=100.0, description="Blood oxygen saturation percentage")
    blood_sugar: Optional[float] = Field(default=None, ge=10.0, le=1000.0, description="Random blood glucose mg/dL")
    pain_score: Optional[int] = Field(default=None, ge=-1, le=10, description="0-10 scale (-1 for unassessed)")


class EncounterCreate(BaseModel):
    """Payload to create an outpatient visit encounter."""
    patient_code: str = Field(..., description="Target patient identifier, e.g. PAT-1001")
    department: str = Field(default="General Medicine", description="Consultation department")
    visit_type: str = Field(default="NEW", description="'NEW' for first card or 'RETURNING' for follow-up")
    chief_complaint: str = Field(..., min_length=2, description="Primary presenting complaint")
    complaint_category: Optional[str] = Field(default="General", description="Organ system, e.g. Respiratory, ENT")
    symptom_duration: Optional[str] = Field(default="1 day", description="Duration of symptoms")
    symptoms: List[str] = Field(default_factory=list, description="List of recognized symptom tags")
    vitals: VitalSignsInput = Field(default_factory=VitalSignsInput)
    measurement_source: str = Field(default="TRIAGE_STATION", description="Source of intake vitals")
    mental_status: Optional[str] = Field(default="Alert", description="Alert, Confused, Lethargic, Unresponsive")


class EncounterResponse(BaseModel):
    """Structured outpatient encounter record."""
    encounter_id: str
    patient_code: str
    patient_name: str
    department: str
    arrival_time: str
    visit_type: str
    chief_complaint: str
    complaint_category: str
    symptom_duration: str
    symptoms: List[str]
    vitals: Dict[str, Any]
    missingness_indicators: Dict[str, bool]
    is_emergency: bool
    escalation_level: str
    escalation_reasons: List[str]
    action_required: str
    status: str  # WAITING, WITH_DOCTOR, COMPLETED, ESCALATED_EMERGENCY
    created_at: str
