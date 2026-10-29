"""API Router for LLM-assisted Clinical Decision-Support Summaries."""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status

from app.routers.auth import get_current_user, require_doctor
from app.schemas.ai_summary import (
    AISummaryCreateRequest,
    AISummaryResponse,
    AISummaryReviewRequest,
)
from app.services.llm_service import ai_summary_service

logger = logging.getLogger("medqueue.routers.summaries")
router = APIRouter(tags=["Clinical Decision Support Summaries"])


@router.post(
    "/summaries/encounter/{encounter_id}",
    response_model=AISummaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Grounded Clinical Decision-Support Summary",
)
@router.post(
    "/encounters/{encounter_id}/clinical-summary",
    response_model=AISummaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Grounded Clinical Decision-Support Summary (REST shape)",
)
def generate_summary(
    encounter_id: str,
    payload: Optional[AISummaryCreateRequest] = None,
    current_user: dict = Depends(get_current_user),
) -> AISummaryResponse:
    """Generate structured clinical summary for an encounter, grounded in vitals, complaints, and verified history."""
    try:
        pref = payload.provider_override if payload else None
        return ai_summary_service.generate_encounter_summary(encounter_id=encounter_id, provider_preference=pref)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as exc:
        logger.error(f"Summary generation failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Clinical summary generation failed: {str(exc)}",
        )


@router.get(
    "/summaries/encounter/{encounter_id}",
    response_model=AISummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch Clinical Decision-Support Summary for Encounter",
)
@router.get(
    "/encounters/{encounter_id}/clinical-summary",
    response_model=AISummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch Clinical Decision-Support Summary (REST shape)",
)
def get_summary(
    encounter_id: str,
    current_user: dict = Depends(get_current_user),
) -> AISummaryResponse:
    """Retrieve existing summary for an encounter, checking for staleness."""
    summary = ai_summary_service.get_encounter_summary(encounter_id=encounter_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No summary generated yet for encounter '{encounter_id}'.",
        )
    return summary


@router.patch(
    "/summaries/encounter/{encounter_id}/review",
    response_model=AISummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Doctor Review Checkpoint (Accept, Edit, Reject)",
)
def review_summary(
    encounter_id: str,
    review_req: AISummaryReviewRequest,
    current_user: dict = Depends(require_doctor),
) -> AISummaryResponse:
    """Doctor verification checkpoint: mark summary as ACCEPTED, EDITED, or REJECTED with notes."""
    doctor_id = getattr(current_user, "user_id", None) or (current_user.get("_id") if isinstance(current_user, dict) else "DOC-UNKNOWN")
    try:
        return ai_summary_service.review_summary(
            encounter_id=encounter_id,
            review_req=review_req,
            doctor_id=str(doctor_id),
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as exc:
        logger.error(f"Review update failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record review: {str(exc)}",
        )


@router.post(
    "/clinical-summaries/{summary_id}/review",
    response_model=AISummaryResponse,
    summary="Doctor Review Checkpoint by summary_id",
)
def review_summary_by_id(
    summary_id: str,
    review_req: AISummaryReviewRequest,
    current_user: dict = Depends(require_doctor),
) -> AISummaryResponse:
    """Review summary referencing summary_id."""
    from app.database.mongodb import get_mongodb
    db = get_mongodb()
    doc = db.ai_summaries.find_one({"$or": [{"summary_id": summary_id}, {"_id": summary_id}]})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Summary '{summary_id}' not found.")
    enc_id = doc["encounter_id"]
    return review_summary(encounter_id=enc_id, review_req=review_req, current_user=current_user)


@router.post(
    "/clinical-summaries/{summary_id}/regenerate",
    response_model=AISummaryResponse,
    summary="Regenerate Clinical Summary after source document updates",
)
def regenerate_summary_by_id(
    summary_id: str,
    current_user: dict = Depends(get_current_user),
) -> AISummaryResponse:
    """Regenerate a clinical summary incorporating newly uploaded/verified records."""
    from app.database.mongodb import get_mongodb
    db = get_mongodb()
    doc = db.ai_summaries.find_one({"$or": [{"summary_id": summary_id}, {"_id": summary_id}]})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Summary '{summary_id}' not found.")
    enc_id = doc["encounter_id"]
    return ai_summary_service.generate_encounter_summary(encounter_id=enc_id)
