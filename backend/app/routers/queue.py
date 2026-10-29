"""Active Queue Management Router (MongoDB-backed)."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.schemas.queue import (
    QueueItemCreate,
    QueueItemResponse,
    QueueOverridePayload,
    QueueConfigPayload,
    QueueSeveritySummary,
)
from app.schemas.auth import UserResponse
from app.routers.auth import get_current_user, require_doctor, oauth2_scheme
from app.core.security import decode_access_token
from app.services.auth_service import get_user_by_email
from app.services.queue_engine import (
    enqueue_encounter,
    get_active_queue_list,
    call_patient,
    transition_queue_status,
    apply_doctor_override,
    get_queue_config,
    set_queue_config,
    get_queue_severity_summary,
)

router = APIRouter(prefix="/queue", tags=["Queue Management Engine"])


def get_caller_staff(token: Optional[str] = Depends(oauth2_scheme)) -> str:
    """Resolve calling staff member identity (Doctor, Receptionist, or attending clinical staff)."""
    if token:
        try:
            payload = decode_access_token(token)
            if payload and "sub" in payload:
                user = get_user_by_email(payload["sub"])
                if user:
                    return f"{user['full_name']} ({user['role']})"
        except Exception:
            pass
    return "Dr. Attending Physician (Doctor)"


@router.get(
    "",
    response_model=List[QueueItemResponse],
    summary="Get active queue list with dynamic policy scheduling",
    description="Returns current waiting & in-consultation patients, ordered dynamically by active policy (FCFS, CONVENTIONAL_PRIORITY, or DYNAMIC_HYBRID).",
)
def list_queue(
    policy: Optional[str] = Query(
        default=None,
        pattern="^(FCFS|CONVENTIONAL_PRIORITY|DYNAMIC_HYBRID)$",
        description="Optional policy override for simulation or doctor review",
    ),
) -> List[QueueItemResponse]:
    """Retrieve active waiting queue ordered by active policy."""
    return get_active_queue_list(policy_override=policy)


@router.post(
    "",
    response_model=QueueItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enqueue patient encounter",
    description="Allocates sequential daily token number and enqueues patient.",
)
def enqueue_patient(payload: QueueItemCreate) -> QueueItemResponse:
    """Enqueue encounter into active queue."""
    try:
        return enqueue_encounter(payload)
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to enqueue patient: {str(exc)}",
        )


@router.get(
    "/summary",
    response_model=QueueSeveritySummary,
    summary="Queue acuity counts and operational summary",
)
def queue_summary() -> QueueSeveritySummary:
    """Get acuity breakdown and waiting counts."""
    return get_queue_severity_summary()


@router.post(
    "/call-next",
    response_model=QueueItemResponse,
    summary="Call next highest-ranked patient",
)
def call_next(
    room_number: str = Query(default="OPD Room 1"),
    caller_name: str = Depends(get_caller_staff),
) -> QueueItemResponse:
    """Call front-most patient into doctor or receptionist room."""
    try:
        return call_patient(
            room_number=room_number,
            doctor_name=caller_name,
        )
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))


@router.post(
    "/{entry_id}/call",
    response_model=QueueItemResponse,
    summary="Call specific patient by entry ID",
)
def call_selected_patient(
    entry_id: str,
    room_number: str = Query(default="OPD Room 1"),
    caller_name: str = Depends(get_caller_staff),
) -> QueueItemResponse:
    """Call specific patient by entry_id or patient_code."""
    try:
        return call_patient(
            entry_id=entry_id,
            room_number=room_number,
            doctor_name=caller_name,
        )
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))


@router.post(
    "/{entry_id}/start",
    response_model=QueueItemResponse,
    summary="Start doctor consultation",
)
def start_consultation(
    entry_id: str,
    caller_name: str = Depends(get_caller_staff),
) -> QueueItemResponse:
    """Mark patient consultation as IN_CONSULTATION."""
    try:
        return transition_queue_status(entry_id, "IN_CONSULTATION", caller_name)
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))


@router.post(
    "/{entry_id}/complete",
    response_model=QueueItemResponse,
    summary="Complete consultation",
)
def complete_consultation(
    entry_id: str,
    caller_name: str = Depends(get_caller_staff),
) -> QueueItemResponse:
    """Mark patient consultation as COMPLETED."""
    try:
        return transition_queue_status(entry_id, "COMPLETED", caller_name)
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))


@router.post(
    "/{entry_id}/override",
    response_model=QueueItemResponse,
    summary="Doctor manual priority override",
    description="Authorized doctor adjusts priority level with mandatory textual rationale.",
)
def override_priority(
    entry_id: str,
    payload: QueueOverridePayload,
    current_user: UserResponse = Depends(require_doctor),
) -> QueueItemResponse:
    """Doctor override of triage priority."""
    try:
        return apply_doctor_override(
            entry_id=entry_id,
            payload=payload,
            doctor_id=f"{current_user.full_name} ({current_user.role})",
        )
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))


@router.get(
    "/config",
    summary="Get queue policy configuration",
)
def get_config():
    """Retrieve active policy and starvation parameters."""
    cfg = get_queue_config()
    cfg.pop("_id", None)
    return cfg


@router.post(
    "/config",
    summary="Update queue policy configuration",
)
def update_config(
    payload: QueueConfigPayload,
    current_user: UserResponse = Depends(get_current_user),
):
    """Update active scheduling policy."""
    cfg = set_queue_config(payload)
    cfg.pop("_id", None)
    return cfg
