"""Pydantic schemas for Patients and Visits."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.triage import PriorityFactor


class VisitBase(BaseModel):
    """Common visit attributes."""
    symptoms: List[str] = Field(default_factory=list)
    temperature: Optional[float] = Field(default=98.6)
    heart_rate: Optional[int] = Field(default=75)
    spo2: Optional[int] = Field(default=98)
    blood_pressure: Optional[str] = Field(default="120/80")
    sugar_level: Optional[float] = Field(default=100.0)
    previous_diseases: Optional[List[str]] = Field(default_factory=list)


class VisitCreate(VisitBase):
    """Payload to create a new visit for a patient."""
    patient_id: Optional[str] = Field(default=None, description="External patient code like PAT-1001")


class VisitResponse(VisitBase):
    """Visit output details."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    visit_id: str
    patient_id: int
    visit_date: str
    visit_time: str
    priority_score: int
    severity: str
    risk_factors: Optional[List[PriorityFactor]] = None
    status: str
    created_at: datetime


class PatientBase(BaseModel):
    """Base patient data fields."""
    full_name: str = Field(min_length=1, max_length=255)
    age: int = Field(ge=0, le=130)
    gender: str = Field(default="Other")
    contact: str = Field(min_length=5, max_length=64)
    emergency_contact: Optional[str] = Field(default=None, max_length=64)
    blood_group: Optional[str] = Field(default=None, max_length=16)
    address: Optional[str] = Field(default=None, max_length=255)
    chronic_conditions: Optional[List[str]] = Field(default_factory=list)


class PatientCreate(PatientBase):
    """Payload to register a new patient."""
    patient_id: Optional[str] = Field(default=None, description="Optional custom ID; auto-generated if omitted")
    initial_visit: Optional[VisitBase] = Field(default=None, description="Optional initial visit triage vitals")


class PatientUpdate(BaseModel):
    """Fields that can be updated on an existing patient record."""
    full_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    contact: Optional[str] = None
    emergency_contact: Optional[str] = None
    blood_group: Optional[str] = None
    address: Optional[str] = None
    chronic_conditions: Optional[List[str]] = None


class PatientResponse(PatientBase):
    """Patient record response including historical visits."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: str
    created_at: datetime
    updated_at: datetime
    visits: List[VisitResponse] = Field(default_factory=list)
