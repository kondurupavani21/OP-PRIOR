"""Pydantic schemas for Consultations."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ConsultationCreate(BaseModel):
    """Payload to record a completed patient consultation."""
    patient_id: str = Field(description="Patient ID code, e.g. PAT-1001")
    doctor_name: Optional[str] = Field(default="Dr. Assigned")
    diagnosis: str = Field(min_length=1, description="Clinical diagnosis")
    symptoms: Optional[str] = Field(default=None, description="Observed symptoms")
    prescription: Optional[str] = Field(default=None, description="Prescribed medications & dosages")
    vital_signs: Optional[str] = Field(default=None, description="Vitals observed during consultation")
    notes: Optional[str] = Field(default=None, description="Physician notes or advice")
    follow_up_date: Optional[str] = Field(default=None, description="Recommended follow-up date YYYY-MM-DD")


class ConsultationResponse(BaseModel):
    """Consultation record output schema."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    patient_code: Optional[str] = None
    doctor_name: str
    consultation_date: str
    consultation_time: str
    diagnosis: str
    symptoms: Optional[str] = None
    prescription: Optional[str] = None
    vital_signs: Optional[str] = None
    notes: Optional[str] = None
    follow_up_date: Optional[str] = None
    created_at: datetime
