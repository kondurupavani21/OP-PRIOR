"""Router for Patient-Reported and Extracted External Previous Consultations."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.previous_consultation import (
    PreviousConsultationCreate,
    PreviousConsultationUpdate,
    PreviousConsultationResponse,
)
from app.schemas.auth import UserResponse
from app.routers.auth import get_current_user, require_doctor
from app.services.previous_consultation_service import (
    create_previous_consultation,
    get_patient_previous_consultations,
    get_previous_consultation_by_id,
    update_previous_consultation,
    delete_previous_consultation,
)

router = APIRouter(tags=["Previous Consultations"])


@router.post(
    "/patients/{patient_code}/previous-consultations",
    response_model=PreviousConsultationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record an external previous consultation",
    description="Captures patient-reported previous clinic visits, symptoms, past diagnoses, treatments, and response.",
)
def record_previous_consultation(
    patient_code: str,
    payload: PreviousConsultationCreate,
) -> PreviousConsultationResponse:
    """Record patient-reported previous consultation."""
    try:
        # Guarantee patient_code matches route
        payload.patient_code = patient_code
        return create_previous_consultation(payload)
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to record previous consultation: {str(exc)}",
        )


@router.get(
    "/patients/{patient_code}/previous-consultations",
    response_model=List[PreviousConsultationResponse],
    summary="List patient previous consultations",
    description="Retrieve all patient-reported and extracted external consultations for a patient.",
)
def list_patient_previous_consultations(patient_code: str) -> List[PreviousConsultationResponse]:
    """Fetch previous consultations for a patient."""
    return get_patient_previous_consultations(patient_code)


@router.get(
    "/previous-consultations/{consultation_id}",
    response_model=PreviousConsultationResponse,
    summary="Get previous consultation by ID",
)
def get_previous_consultation(consultation_id: str) -> PreviousConsultationResponse:
    """Fetch single previous consultation by consultation_id."""
    pcon = get_previous_consultation_by_id(consultation_id)
    if not pcon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Previous consultation '{consultation_id}' not found.",
        )
    return pcon


@router.patch(
    "/previous-consultations/{consultation_id}",
    response_model=PreviousConsultationResponse,
    summary="Update or clinician-verify a previous consultation record",
)
def update_consultation_record(
    consultation_id: str,
    payload: PreviousConsultationUpdate,
    current_user: Optional[UserResponse] = Depends(get_current_user),
) -> PreviousConsultationResponse:
    """Update details or mark previous consultation as verified."""
    try:
        verifier_str = f"{current_user.full_name} ({current_user.role})" if current_user else "Authorized Staff"
        return update_previous_consultation(
            consultation_id=consultation_id,
            payload=payload,
            verifier_id=verifier_str,
        )
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update previous consultation: {str(exc)}",
        )


@router.patch(
    "/previous-consultations/{consultation_id}/verify",
    response_model=PreviousConsultationResponse,
    summary="Clinician verification of a previous consultation note",
)
def verify_consultation_record(
    consultation_id: str,
    payload: Optional[dict] = None,
    current_user: Optional[UserResponse] = Depends(get_current_user),
) -> PreviousConsultationResponse:
    """Explicitly verify previous consultation record with staff notes."""
    notes = (payload or {}).get("notes") if isinstance(payload, dict) else None
    update_data = PreviousConsultationUpdate(is_verified=True, verification_notes=notes)
    verifier_str = current_user.full_name if current_user else "Dr. Sarah Rao, MD"
    try:
        return update_previous_consultation(
            consultation_id=consultation_id,
            payload=update_data,
            verifier_id=verifier_str,
        )
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))


@router.delete(
    "/previous-consultations/{consultation_id}",
    summary="Delete a previous consultation entry",
)
def delete_consultation_record(
    consultation_id: str,
    current_user: Optional[UserResponse] = Depends(get_current_user),
) -> dict:
    """Delete a previous consultation record."""
    success = delete_previous_consultation(consultation_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Previous consultation '{consultation_id}' not found.",
        )
    return {"deleted": True, "consultation_id": consultation_id}
