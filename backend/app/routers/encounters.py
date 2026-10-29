"""Clinical Encounters and Vitals Intake Router (MongoDB-backed)."""
from fastapi import APIRouter, HTTPException, status
from app.schemas.patient_encounter import (
    EncounterCreate,
    EncounterResponse,
)
from app.services.patient_encounter_service import (
    create_encounter,
    get_encounter_by_id,
)

router = APIRouter(prefix="/encounters", tags=["Encounters & Clinical Intake"])


@router.post(
    "",
    response_model=EncounterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create clinical encounter with synchronous emergency screening",
    description="Records intake vitals, chief complaint, symptom tags, explicit missingness, and runs the emergency screening pathway.",
)
def create_clinical_encounter(payload: EncounterCreate) -> EncounterResponse:
    """Create encounter and execute emergency safety screening."""
    try:
        return create_encounter(payload)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to create clinical encounter: {str(exc)}",
        )


@router.get(
    "/{encounter_id}",
    response_model=EncounterResponse,
    summary="Get encounter details",
    description="Fetch complete intake vitals, missingness flags, and emergency evaluation for an encounter.",
)
def get_encounter(encounter_id: str) -> EncounterResponse:
    """Retrieve encounter details by encounter_id."""
    encounter = get_encounter_by_id(encounter_id)
    if not encounter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Encounter '{encounter_id}' not found.",
        )
    return encounter
