"""Patient Master Profile & Registration Router (MongoDB-backed)."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from app.schemas.patient_encounter import (
    PatientCreate,
    PatientResponse,
    EncounterResponse,
)
from app.services.patient_encounter_service import (
    register_or_match_patient,
    get_patient_by_code,
    search_patients,
    get_encounters_by_patient,
)

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.post(
    "",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new patient or return existing matched profile",
    description="Registers patient demographics with phone-based identity matching to prevent duplicate patient records.",
)
def register_patient(payload: PatientCreate) -> PatientResponse:
    """Register new patient or retrieve existing profile."""
    try:
        patient, is_new = register_or_match_patient(payload)
        return patient
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to process patient registration: {str(exc)}",
        )


@router.get(
    "",
    response_model=List[PatientResponse],
    summary="Search patient directory",
    description="Search patient records by name, phone contact, or patient ID code.",
)
def list_patients(
    query: Optional[str] = Query(default=None, description="Search term for name, contact, or patient ID"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> List[PatientResponse]:
    """Search and paginate patient master records."""
    return search_patients(query=query, skip=skip, limit=limit)


@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Get patient profile by code",
    description="Fetch a patient's complete demographic and encounter metadata.",
)
def get_patient(patient_id: str) -> PatientResponse:
    """Fetch patient profile by patient_code."""
    patient = get_patient_by_code(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found.",
        )
    return patient


@router.get(
    "/{patient_id}/encounters",
    response_model=List[EncounterResponse],
    summary="Get all historical encounters for a patient",
    description="Fetches chronological list of clinical visits and intake vitals for the specified patient.",
)
def list_patient_encounters(patient_id: str) -> List[EncounterResponse]:
    """Retrieve historical encounters for a patient."""
    patient = get_patient_by_code(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found.",
        )
    return get_encounters_by_patient(patient_id)
