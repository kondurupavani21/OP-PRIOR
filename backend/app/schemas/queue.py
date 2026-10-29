"""Pydantic v2 schemas for Doctor Queue Management, Policies, and Manual Overrides."""
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class QueueItemCreate(BaseModel):
    """Payload to enqueue a patient encounter."""
    patient_code: str = Field(..., description="Target patient identifier")
    encounter_id: str = Field(..., description="Target clinical encounter identifier")
    department: str = Field(default="General Medicine")
    initial_priority: int = Field(default=3, ge=1, le=5, description="Initial triage priority level (1=Immediate to 5=Non-urgent)")


class QueueItemUpdate(BaseModel):
    """Update payload for queue item status or priority."""
    status: Optional[str] = None
    priority_score: Optional[int] = None
    severity: Optional[str] = None
    assigned_room: Optional[str] = None


class QueueOverridePayload(BaseModel):
    """Clinician manual override payload with mandatory reason."""
    new_priority: int = Field(..., ge=1, le=5, description="Clinician-approved priority tier (1 to 5)")
    override_reason: str = Field(..., min_length=5, max_length=500, description="Mandatory clinical justification for override")
    clinical_rationale: Optional[str] = Field(default=None, description="Optional detailed doctor note")


class QueueConfigPayload(BaseModel):
    """Configuration payload for switching active queue policy and starvation limits."""
    active_policy: str = Field(
        default="DYNAMIC_HYBRID",
        pattern="^(FCFS|CONVENTIONAL_PRIORITY|DYNAMIC_HYBRID)$",
        description="Queue scheduling policy: FCFS, CONVENTIONAL_PRIORITY, or DYNAMIC_HYBRID",
    )
    starvation_threshold_minutes: int = Field(default=45, ge=10, le=240, description="Waiting time threshold where aging boost begins")
    priority_weight: float = Field(default=1.0, ge=0.1, le=5.0)
    wait_weight: float = Field(default=0.5, ge=0.0, le=5.0)


class QueueItemResponse(BaseModel):
    """Full queue item representation returned to doctor dashboard and queue viewers."""
    entry_id: str
    token_number: int
    patient_code: str
    patient_name: str
    encounter_id: str
    department: str
    arrival_time: str
    waiting_time_minutes: int = 0
    current_position: int = 1
    recommended_priority: int = 3
    clinician_approved_priority: int = 3
    queue_status: str = Field(default="WAITING", description="WAITING, CALLED, IN_CONSULTATION, COMPLETED, CANCELLED")
    assigned_room: Optional[str] = None
    is_emergency: bool = False
    is_overridden: bool = False
    override_reason: Optional[str] = None
    active_policy: str = "DYNAMIC_HYBRID"
    rank_score: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class QueueSeveritySummary(BaseModel):
    """Summary of active waiting queue acuity counts."""
    total_active: int = 0
    total_waiting: int = 0
    total_in_consultation: int = 0
    total_completed_today: int = 0
    critical_count: int = 0      # Level 1
    emergent_count: int = 0      # Level 2
    urgent_count: int = 0        # Level 3
    less_urgent_count: int = 0   # Level 4
    non_urgent_count: int = 0    # Level 5
    active_policy: str = "DYNAMIC_HYBRID"
