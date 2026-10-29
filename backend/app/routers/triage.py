"""AI Triage and Priority Scoring API Router."""
from fastapi import APIRouter, status
from app.schemas.triage import TriageInput, TriageResult
from app.services.triage_service import calculate_triage_priority

router = APIRouter(prefix="/triage", tags=["AI Triage & Priority"])


@router.post(
    "/assess",
    response_model=TriageResult,
    status_code=status.HTTP_200_OK,
    summary="Assess Patient Urgency & Priority Score",
    description="Evaluates vital signs, symptoms, and risk factors to generate an algorithmic urgency score (0-100) and severity classification.",
)
def assess_patient_triage(payload: TriageInput) -> TriageResult:
    """Run real-time clinical triage assessment."""
    return calculate_triage_priority(payload)
