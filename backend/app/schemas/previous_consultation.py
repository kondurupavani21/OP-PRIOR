"""Pydantic v2 schemas for Patient-Reported & Extracted Previous Consultations."""
from datetime import datetime, timezone
from typing import List, Optional, Any, Union
from pydantic import BaseModel, Field, ConfigDict, model_validator


def utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PreviousConsultationCreate(BaseModel):
    """Payload to record an external previous consultation."""
    patient_code: Optional[str] = Field(default=None, description="Target patient identifier, e.g. PAT-1001")
    encounter_id: Optional[str] = Field(default=None, description="Optional associated encounter ID")
    facility_name: Optional[str] = Field(default=None, description="Previous hospital or clinic")
    facility_or_doctor: Optional[str] = Field(default=None, description="Alternative facility / doctor name")
    doctor_name: Optional[str] = Field(default=None, description="Previous doctor name if known")
    consultation_date: Optional[str] = Field(default=None, description="Consultation date YYYY-MM-DD or approx")
    previous_symptoms: Optional[Union[List[str], str]] = Field(default_factory=list, description="Symptoms reported")
    symptoms_reported: Optional[str] = Field(default=None, description="Alternative symptoms reported text")
    previous_diagnosis: Optional[str] = Field(default=None, description="Previous diagnosis")
    diagnosis_given: Optional[str] = Field(default=None, description="Alternative diagnosis text")
    previous_investigations: Optional[Union[List[str], str]] = Field(default_factory=list, description="Previous investigations")
    investigations_done: Optional[str] = Field(default=None, description="Alternative investigations text")
    treatment_prescribed: Optional[str] = Field(default=None, description="Treatment or therapy advised")
    medicines_taken: Optional[Union[List[str], str]] = Field(default_factory=list, description="Medicines taken")
    duration_of_treatment: Optional[str] = Field(default=None, description="Duration of previous treatment")
    treatment_response: Optional[str] = Field(
        default="UNCHANGED",
        description="Response to treatment: IMPROVED, UNCHANGED, WORSENED, NOT_SURE",
    )
    response_to_treatment: Optional[str] = Field(default=None, description="Alternative treatment response field")
    side_effects_reported: Optional[str] = Field(default=None, description="Reported side effects")
    side_effects_or_issues: Optional[str] = Field(default=None, description="Alternative side effects field")
    notes: Optional[str] = Field(default=None, description="Additional contextual observations")
    source_provenance: str = Field(
        default="PATIENT_REPORTED",
        description="PATIENT_REPORTED, DOCUMENT_EXTRACTED, CLINICIAN_VERIFIED",
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        # Normalize facility
        if "facility_or_doctor" in data and not data.get("facility_name"):
            data["facility_name"] = data["facility_or_doctor"]
        elif "facility_name" in data and not data.get("facility_or_doctor"):
            data["facility_or_doctor"] = data["facility_name"]

        # Normalize symptoms
        if "symptoms_reported" in data and not data.get("previous_symptoms"):
            raw = data["symptoms_reported"]
            data["previous_symptoms"] = [s.strip() for s in raw.split(",") if s.strip()] if isinstance(raw, str) else raw

        # Normalize diagnosis
        if "diagnosis_given" in data and not data.get("previous_diagnosis"):
            data["previous_diagnosis"] = data["diagnosis_given"]

        # Normalize investigations
        if "investigations_done" in data and not data.get("previous_investigations"):
            raw = data["investigations_done"]
            data["previous_investigations"] = [s.strip() for s in raw.split(",") if s.strip()] if isinstance(raw, str) else raw

        # Normalize medicines
        if "medicines_taken" in data and isinstance(data["medicines_taken"], str):
            raw = data["medicines_taken"]
            data["medicines_taken"] = [s.strip() for s in raw.split(",") if s.strip()]

        # Normalize response
        if "response_to_treatment" in data and not data.get("treatment_response"):
            data["treatment_response"] = str(data["response_to_treatment"]).upper()
        elif "treatment_response" in data:
            data["treatment_response"] = str(data["treatment_response"]).upper()

        # Normalize side effects
        if "side_effects_or_issues" in data and not data.get("side_effects_reported"):
            data["side_effects_reported"] = data["side_effects_or_issues"]

        return data


class PreviousConsultationUpdate(BaseModel):
    """Payload to update/patch an existing previous consultation record."""
    facility_name: Optional[str] = None
    doctor_name: Optional[str] = None
    consultation_date: Optional[str] = None
    previous_symptoms: Optional[Union[List[str], str]] = None
    previous_diagnosis: Optional[str] = None
    previous_investigations: Optional[Union[List[str], str]] = None
    treatment_prescribed: Optional[str] = None
    medicines_taken: Optional[Union[List[str], str]] = None
    duration_of_treatment: Optional[str] = None
    treatment_response: Optional[str] = None
    response_to_treatment: Optional[str] = None
    side_effects_reported: Optional[str] = None
    notes: Optional[str] = None
    is_verified: Optional[bool] = None
    verification_notes: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_update(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "response_to_treatment" in data and not data.get("treatment_response"):
                data["treatment_response"] = str(data["response_to_treatment"]).upper()
            elif "treatment_response" in data:
                data["treatment_response"] = str(data["treatment_response"]).upper()
        return data


class PreviousConsultationResponse(BaseModel):
    """Structured representation of a previous consultation."""
    consultation_id: str
    id: Optional[str] = None
    patient_code: str
    encounter_id: Optional[str] = None
    facility_name: Optional[str] = None
    facility_or_doctor: Optional[str] = None
    doctor_name: Optional[str] = None
    consultation_date: Optional[str] = None
    previous_symptoms: List[str] = Field(default_factory=list)
    previous_diagnosis: Optional[str] = None
    previous_investigations: List[str] = Field(default_factory=list)
    treatment_prescribed: Optional[str] = None
    medicines_taken: List[str] = Field(default_factory=list)
    duration_of_treatment: Optional[str] = None
    treatment_response: str = "UNCHANGED"
    response_to_treatment: str = "UNCHANGED"
    side_effects_reported: Optional[str] = None
    source_provenance: str = "PATIENT_REPORTED"
    is_verified: bool = False
    verified_by_staff: bool = False
    verified_by: Optional[str] = None
    verified_by_name: Optional[str] = None
    verified_at: Optional[str] = None
    notes: Optional[str] = None
    created_at: str = Field(default_factory=utc_iso_now)
    updated_at: str = Field(default_factory=utc_iso_now)

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def sync_compatibility_fields(self) -> "PreviousConsultationResponse":
        if not self.id:
            self.id = self.consultation_id
        if not self.facility_or_doctor:
            self.facility_or_doctor = self.facility_name or self.doctor_name or "External Clinic"
        self.response_to_treatment = self.treatment_response
        self.verified_by_staff = self.is_verified
        if self.verified_by and not self.verified_by_name:
            self.verified_by_name = self.verified_by
        return self
