"""Pydantic schemas for AI triage and priority assessment."""
from typing import List, Optional
from pydantic import BaseModel, Field


class PriorityFactor(BaseModel):
    """Detailed clinical or physiological factor contributing to priority score."""
    title: str = Field(description="Factor name / alert title")
    description: str = Field(description="Explanatory diagnostic detail")
    points: str = Field(description="Point contribution, e.g. +32")
    level: str = Field(description="Severity tier: critical, warning, or normal")


class TriageInput(BaseModel):
    """Input payload for clinical priority calculation."""
    age: int = Field(ge=0, le=130, description="Patient age in years")
    gender: Optional[str] = Field(default="Other", description="Patient gender")
    symptoms: List[str] = Field(default_factory=list, description="List of presenting symptoms")
    temperature: Optional[float] = Field(default=98.6, description="Body temperature in Fahrenheit (°F)")
    heart_rate: Optional[int] = Field(default=75, description="Heart pulse rate in beats per minute (bpm)")
    spo2: Optional[int] = Field(default=98, description="Blood oxygen saturation percentage (0-100%)")
    blood_pressure: Optional[str] = Field(default="120/80", description="Systolic/Diastolic blood pressure, e.g. 120/80")
    sugar_level: Optional[float] = Field(default=100.0, description="Blood glucose level (mg/dL)")
    previous_diseases: Optional[List[str]] = Field(default_factory=list, description="Known chronic or preexisting conditions")


class TriageResult(BaseModel):
    """Comprehensive triage assessment output."""
    priority_score: int = Field(ge=0, le=100, description="Calculated urgency score between 0 and 100")
    severity: str = Field(description="Severity categorization: HIGH, MEDIUM, or LOW")
    is_emergency: bool = Field(description="True if patient requires urgent/immediate medical attention")
    recommended_wait_mins: int = Field(description="Target maximum waiting window in minutes")
    factors: List[PriorityFactor] = Field(default_factory=list, description="Breakdown of clinical risk factors")
    summary: str = Field(description="Human-readable triage recommendation summary")
