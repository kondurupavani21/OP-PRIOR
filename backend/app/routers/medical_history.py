"""Verified Medical History Router (MongoDB-backed)."""
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.medical_history import (
    PatientHistorySummaryResponse,
    MedicalHistoryItem,
    MedicalHistoryCreate,
)
from app.schemas.auth import UserResponse
from app.routers.auth import get_current_user, require_doctor
from app.services.medical_history_service import (
    get_patient_history_summary,
    add_manual_history_item,
)

router = APIRouter(prefix="/patients", tags=["Verified Medical History"])


@router.get(
    "/{patient_code}/history",
    response_model=PatientHistorySummaryResponse,
    summary="Get verified longitudinal medical history",
    description="Returns verified conditions, medications, and allergies with explicit source provenance and pending document indicators.",
)
def get_patient_history(patient_code: str) -> PatientHistorySummaryResponse:
    """Retrieve verified medical history for a patient."""
    return get_patient_history_summary(patient_code)


@router.post(
    "/{patient_code}/history",
    response_model=MedicalHistoryItem,
    status_code=status.HTTP_201_CREATED,
    summary="Clinician record of verified medical fact",
    description="Allows authorized clinicians to append a verified clinical condition or allergy with audit tracking.",
)
def add_history_entry(
    patient_code: str,
    payload: MedicalHistoryCreate,
    current_user: UserResponse = Depends(require_doctor),
) -> MedicalHistoryItem:
    """Record verified clinical history item."""
    try:
        return add_manual_history_item(
            patient_code=patient_code,
            payload=payload,
            verifier_id=f"{current_user.full_name} ({current_user.role})",
        )
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to record history entry: {str(exc)}",
        )
