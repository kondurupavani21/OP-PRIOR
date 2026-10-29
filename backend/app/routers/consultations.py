"""Consultations API router."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.consultation import ConsultationCreate, ConsultationResponse
from app.services.consultation_service import (
    create_consultation,
    get_consultations_by_patient,
    list_recent_consultations,
)

router = APIRouter(prefix="/consultations", tags=["Consultations"])


@router.post(
    "",
    response_model=ConsultationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a doctor consultation",
    description="Saves diagnosis, prescription, and notes while marking patient's queue status as COMPLETED.",
)
def record_consultation(
    payload: ConsultationCreate,
    db: Session = Depends(get_db),
) -> ConsultationResponse:
    """Record a completed consultation."""
    try:
        return create_consultation(db, payload)
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error recording consultation: {str(exc)}",
        )


@router.get(
    "",
    response_model=List[ConsultationResponse],
    summary="List consultations",
    description="Fetch recent consultations with optional date filter.",
)
def get_consultations(
    date: Optional[str] = Query(default=None, description="Date filter YYYY-MM-DD"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> List[ConsultationResponse]:
    """Retrieve historical consultations."""
    return list_recent_consultations(db, date_str=date, limit=limit)


@router.get(
    "/patient/{patient_id}",
    response_model=List[ConsultationResponse],
    summary="Get patient consultation history",
    description="Retrieve all consultations documented for a given patient.",
)
def get_patient_consultations(
    patient_id: str,
    db: Session = Depends(get_db),
) -> List[ConsultationResponse]:
    """Fetch consultations for a single patient."""
    return get_consultations_by_patient(db, patient_id)
