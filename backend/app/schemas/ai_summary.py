"""Pydantic schemas for LLM-assisted Clinical Encounter Summaries with 7 Clinical Sections."""
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class DifferentialItem(BaseModel):
    """Differential diagnosis candidate with clinical rationale."""
    condition_name: str
    likelihood: str = Field(..., description="High, Moderate, Consider/Rule Out")
    clinical_rationale: str
    suggested_workup: List[str] = Field(default_factory=list)


class GroundedCitation(BaseModel):
    """Traceable evidence citation connecting summary claims to patient EHR source."""
    claim: str
    source_type: str = Field(..., description="PATIENT_REPORTED, DOCUMENT_OCR, VERIFIED_HISTORY, VITALS, CHIEF_COMPLAINT")
    source_reference: str
    document_id: Optional[str] = None
    page_number: Optional[int] = None
    verification_status: str = Field(default="UNVERIFIED", description="VERIFIED, UNVERIFIED, PATIENT_REPORTED")


class ClinicalTimelineEvent(BaseModel):
    """Chronological event in patient's clinical timeline."""
    event_date: Optional[str] = None
    event_type: str = Field(..., description="CONSULTATION, INVESTIGATION, MEDICATION, CURRENT_PRESENTATION")
    description: str
    source_document_id: Optional[str] = None
    is_uncertain_date: bool = False


class PreviousConsultationSummaryItem(BaseModel):
    """Structured clinical summary of a past consultation."""
    facility_or_doctor: str
    consultation_date: Optional[str] = None
    documented_diagnosis: Optional[str] = None
    treatment_recorded: Optional[str] = None
    patient_reported_adherence: Optional[str] = None
    reported_response: str = "UNCHANGED"
    source_type: str = "PATIENT_REPORTED"


class PreviousInvestigationSummaryItem(BaseModel):
    """Structured previous laboratory or radiology finding."""
    test_name: str
    result: str
    units: Optional[str] = None
    reference_range: Optional[str] = None
    investigation_date: Optional[str] = None
    is_abnormal: bool = False
    source_document_id: Optional[str] = None


class AISummaryCreateRequest(BaseModel):
    """Request to generate grounded clinical decision-support summary."""
    encounter_id: str
    provider_override: Optional[str] = Field(default=None, description="mock, openai, or ollama")


class AISummaryReviewRequest(BaseModel):
    """Doctor acceptance, edit, or rejection of AI-generated summary."""
    status: str = Field(..., description="ACCEPTED, EDITED, REJECTED")
    doctor_notes: Optional[str] = None
    edited_summary_text: Optional[str] = None


class AISummaryResponse(BaseModel):
    """Grounded clinical decision-support summary structured across 7 key clinical domains."""
    id: str
    encounter_id: str
    patient_id: str

    # Legacy & Quick Snapshot Fields (Full Backward Compatibility)
    chief_complaint_synopsis: str
    vitals_objective_assessment: str
    verified_comorbidities_context: List[str]
    differential_considerations: List[DifferentialItem]
    recommended_workup: List[str]
    escalation_flags: List[str]
    grounded_citations: List[GroundedCitation]

    # Required 7 Structured Clinical Sections
    # Section A: Current Presentation
    section_a_current_presentation: Dict[str, Any] = Field(default_factory=dict)
    # Section B: Previous Consultations
    section_b_previous_consultations: List[PreviousConsultationSummaryItem] = Field(default_factory=list)
    # Section C: Previous Investigations
    section_c_previous_investigations: List[PreviousInvestigationSummaryItem] = Field(default_factory=list)
    # Section D: Relevant Medical History
    section_d_relevant_medical_history: Dict[str, Any] = Field(default_factory=dict)
    # Section E: Clinical Timeline
    section_e_clinical_timeline: List[ClinicalTimelineEvent] = Field(default_factory=list)
    # Section F: Important Uncertainties & Missing Information
    section_f_important_uncertainties: List[str] = Field(default_factory=list)
    # Section G: Traceable Source References
    section_g_source_references: List[GroundedCitation] = Field(default_factory=list)

    # Metadata & State
    provider_used: str
    generation_mode: str = "LLM_SYNTHESIZED"  # LLM_SYNTHESIZED or DETERMINISTIC_FALLBACK
    is_stale: bool = False
    stale_reason: Optional[str] = None
    doctor_review_status: str = Field(default="PENDING_REVIEW")
    doctor_notes: Optional[str] = None
    reviewed_by_doctor_id: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)
