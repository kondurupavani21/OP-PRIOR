"""Persistent MongoDB Queue Engine with 3 Configurable Prioritization Policies.

Supports:
- Policy A: FCFS (First Come, First Served) with emergency bypass
- Policy B: Conventional Priority Queue (Level 1 to 5 with FIFO tie-breaking)
- Policy C: Proposed Dynamic Hybrid Queue (Priority + Waiting-Time Aging Safeguards + Clinician Overrides)
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from app.database.mongodb import (
    get_queue_entries_col,
    get_doctor_overrides_col,
    get_audit_events_col,
    get_announcement_events_col,
    get_encounters_col,
    get_patients_col,
    get_mongodb,
)
from app.schemas.queue import (
    QueueItemCreate,
    QueueItemResponse,
    QueueOverridePayload,
    QueueConfigPayload,
    QueueSeveritySummary,
)


def utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_today_prefix() -> str:
    return datetime.now().strftime("%Y%m%d")


def get_queue_config() -> Dict[str, Any]:
    """Retrieve global queue configuration singleton."""
    col = get_mongodb()["queue_config"]
    cfg = col.find_one({"config_id": "GLOBAL_QUEUE_CONFIG"})
    if not cfg:
        default_cfg = {
            "config_id": "GLOBAL_QUEUE_CONFIG",
            "active_policy": "DYNAMIC_HYBRID",
            "starvation_threshold_minutes": 45,
            "priority_weight": 1.0,
            "wait_weight": 0.5,
            "updated_at": utc_iso_now(),
        }
        col.insert_one(default_cfg)
        return default_cfg
    return cfg


def set_queue_config(payload: QueueConfigPayload) -> Dict[str, Any]:
    """Update active queue scheduling policy and starvation thresholds."""
    col = get_mongodb()["queue_config"]
    col.update_one(
        {"config_id": "GLOBAL_QUEUE_CONFIG"},
        {"$set": {
            "active_policy": payload.active_policy,
            "starvation_threshold_minutes": payload.starvation_threshold_minutes,
            "priority_weight": payload.priority_weight,
            "wait_weight": payload.wait_weight,
            "updated_at": utc_iso_now(),
        }},
        upsert=True,
    )
    return get_queue_config()


def calculate_waiting_time_mins(arrival_iso: str) -> int:
    """Calculate elapsed waiting time in minutes from ISO arrival timestamp."""
    try:
        arr = datetime.fromisoformat(arrival_iso)
        now = datetime.now(timezone.utc)
        if arr.tzinfo is None:
            arr = arr.replace(tzinfo=timezone.utc)
        diff = (now - arr).total_seconds() / 60.0
        return max(0, int(diff))
    except Exception:
        return 0


def compute_rank_score(doc: Dict[str, Any], policy: str, cfg: Dict[str, Any]) -> float:
    """Compute mathematical rank score based on active policy. Higher score = earlier service."""
    waiting_mins = calculate_waiting_time_mins(doc.get("arrival_time", utc_iso_now()))
    priority = int(doc.get("clinician_approved_priority", 3))  # 1 to 5
    is_emergency = doc.get("is_emergency", False)

    # Emergency cases immediately jump to maximum rank across all policies
    if is_emergency:
        return 10000.0 - waiting_mins * 0.1

    if policy == "FCFS":
        # First Come First Served: score proportional to waiting time (earlier arrival = higher score)
        return float(waiting_mins)

    elif policy == "CONVENTIONAL_PRIORITY":
        # Strict priority tiers: Level 1 (Score 5000), Level 2 (4000), ..., Level 5 (1000) + arrival minutes
        tier_score = (6 - priority) * 1000.0
        return tier_score + (waiting_mins * 0.1)

    else:  # DYNAMIC_HYBRID (Policy C)
        # 1. Base Priority Term (Level 1=100 pts, Level 5=20 pts)
        priority_term = (6 - priority) * 20.0 * cfg.get("priority_weight", 1.0)

        # 2. Waiting-Time Aging Safeguard: Prevents lower acuity starvation
        # As waiting time approaches or exceeds starvation threshold, patient gains priority boost
        threshold = max(10, cfg.get("starvation_threshold_minutes", 45))
        aging_ratio = min(2.0, waiting_mins / threshold)
        aging_boost = aging_ratio * 30.0 * cfg.get("wait_weight", 0.5)

        # 3. Clinician Override Boost
        override_bonus = 15.0 if doc.get("is_overridden") else 0.0

        return priority_term + aging_boost + override_bonus


def enqueue_encounter(payload: QueueItemCreate) -> QueueItemResponse:
    """Allocate daily token number and add patient encounter to active queue."""
    col = get_queue_entries_col()
    patient = get_patients_col().find_one({"patient_code": payload.patient_code})
    if not patient:
        raise ValueError(f"Patient with code '{payload.patient_code}' not found.")

    encounter = get_encounters_col().find_one({"encounter_id": payload.encounter_id})
    if not encounter:
        raise ValueError(f"Encounter '{payload.encounter_id}' not found.")

    today = get_today_prefix()

    # Prevent duplicate active queue entries for the same patient today
    active = col.find_one({
        "patient_code": payload.patient_code,
        "entry_id": {"$regex": f"^Q-{today}"},
        "queue_status": {"$in": ["WAITING", "CALLED", "IN_CONSULTATION"]},
    })
    if active:
        cfg = get_queue_config()
        return QueueItemResponse(
            entry_id=active["entry_id"],
            token_number=active["token_number"],
            patient_code=active["patient_code"],
            patient_name=active["patient_name"],
            encounter_id=active["encounter_id"],
            department=active["department"],
            arrival_time=active["arrival_time"],
            waiting_time_minutes=calculate_waiting_time_mins(active["arrival_time"]),
            current_position=1,
            recommended_priority=active.get("recommended_priority", 3),
            clinician_approved_priority=active.get("clinician_approved_priority", 3),
            queue_status=active["queue_status"],
            assigned_room=active.get("assigned_room"),
            is_emergency=active.get("is_emergency", False),
            is_overridden=active.get("is_overridden", False),
            override_reason=active.get("override_reason"),
            active_policy=cfg.get("active_policy", "DYNAMIC_HYBRID"),
            rank_score=0.0,
        )

    # Next daily sequential token
    daily_count = col.count_documents({"entry_id": {"$regex": f"^Q-{today}"}})
    token_num = daily_count + 1
    entry_id = f"Q-{today}-{token_num:03d}"
    now_iso = utc_iso_now()

    is_emergency = encounter.get("is_emergency", False)
    initial_priority = 1 if is_emergency else payload.initial_priority

    queue_doc = {
        "entry_id": entry_id,
        "token_number": token_num,
        "patient_code": payload.patient_code,
        "patient_name": patient["full_name"],
        "encounter_id": payload.encounter_id,
        "department": payload.department,
        "arrival_time": now_iso,
        "recommended_priority": initial_priority,
        "clinician_approved_priority": initial_priority,
        "queue_status": "WAITING",
        "assigned_room": None,
        "is_emergency": is_emergency,
        "is_overridden": False,
        "override_reason": None,
        "created_at": now_iso,
    }

    col.insert_one(queue_doc)

    get_audit_events_col().insert_one({
        "audit_id": f"AUD-{uuid.uuid4().hex[:10]}",
        "action": "QUEUE_ENQUEUED",
        "resource_type": "queue_entry",
        "resource_id": entry_id,
        "timestamp": now_iso,
        "details": f"Token {token_num} issued for {patient['full_name']} (Priority {initial_priority})",
    })

    cfg = get_queue_config()
    return QueueItemResponse(
        entry_id=entry_id,
        token_number=token_num,
        patient_code=payload.patient_code,
        patient_name=patient["full_name"],
        encounter_id=payload.encounter_id,
        department=payload.department,
        arrival_time=now_iso,
        waiting_time_minutes=0,
        current_position=daily_count + 1,
        recommended_priority=initial_priority,
        clinician_approved_priority=initial_priority,
        queue_status="WAITING",
        is_emergency=is_emergency,
        is_overridden=False,
        active_policy=cfg.get("active_policy", "DYNAMIC_HYBRID"),
        rank_score=0.0,
    )


def get_active_queue_list(policy_override: Optional[str] = None) -> List[QueueItemResponse]:
    """Retrieve and sort current waiting queue entries according to active scheduling policy."""
    col = get_queue_entries_col()
    cfg = get_queue_config()
    policy = policy_override or cfg.get("active_policy", "DYNAMIC_HYBRID")

    cursor = col.find({"queue_status": {"$in": ["WAITING", "CALLED", "IN_CONSULTATION"]}})
    raw_list = list(cursor)

    # Compute scores and sort
    scored_items = []
    for doc in raw_list:
        score = compute_rank_score(doc, policy, cfg)
        scored_items.append((score, doc))

    # Sort descending by rank score (highest score first)
    scored_items.sort(key=lambda x: x[0], reverse=True)

    results: List[QueueItemResponse] = []
    for idx, (score, doc) in enumerate(scored_items, start=1):
        waiting_mins = calculate_waiting_time_mins(doc.get("arrival_time", utc_iso_now()))
        results.append(QueueItemResponse(
            entry_id=doc["entry_id"],
            token_number=doc["token_number"],
            patient_code=doc["patient_code"],
            patient_name=doc.get("patient_name", "Unknown"),
            encounter_id=doc["encounter_id"],
            department=doc.get("department", "General Medicine"),
            arrival_time=doc.get("arrival_time", utc_iso_now()),
            waiting_time_minutes=waiting_mins,
            current_position=idx,
            recommended_priority=doc.get("recommended_priority", 3),
            clinician_approved_priority=doc.get("clinician_approved_priority", 3),
            queue_status=doc.get("queue_status", "WAITING"),
            assigned_room=doc.get("assigned_room"),
            is_emergency=doc.get("is_emergency", False),
            is_overridden=doc.get("is_overridden", False),
            override_reason=doc.get("override_reason"),
            active_policy=policy,
            rank_score=round(score, 2),
        ))

    return results


def call_patient(
    entry_id: Optional[str] = None,
    room_number: str = "OPD Room 1",
    doctor_name: str = "Dr. On Duty",
) -> QueueItemResponse:
    """Call the specified or top-ranked waiting patient into consultation."""
    col = get_queue_entries_col()

    if entry_id:
        target = col.find_one({
            "$or": [{"entry_id": entry_id}, {"patient_code": entry_id}],
            "queue_status": "WAITING",
        })
        if not target:
            # Allow re-calling if already in CALLED status
            target = col.find_one({
                "$or": [{"entry_id": entry_id}, {"patient_code": entry_id}],
                "queue_status": "CALLED",
            })
        if not target:
            existing = col.find_one({"$or": [{"entry_id": entry_id}, {"patient_code": entry_id}]})
            if existing:
                raise ValueError(f"Queue entry '{entry_id}' is in '{existing.get('queue_status')}' status.")
            raise ValueError(f"Queue entry '{entry_id}' not found.")
    else:
        # Pick top of active queue
        queue = get_active_queue_list()
        waiting_candidates = [q for q in queue if q.queue_status == "WAITING"]
        if not waiting_candidates:
            raise ValueError("No patients are currently waiting in the queue.")
        target_entry_id = waiting_candidates[0].entry_id
        target = col.find_one({"entry_id": target_entry_id})

    now_iso = utc_iso_now()

    # Update state to CALLED
    col.update_one(
        {"entry_id": target["entry_id"]},
        {"$set": {
            "queue_status": "CALLED",
            "assigned_room": room_number,
            "called_at": now_iso,
            "called_by": doctor_name,
        }}
    )

    # Log Announcement Event with patient name & token details
    get_announcement_events_col().insert_one({
        "event_id": f"ANN-{uuid.uuid4().hex[:8].upper()}",
        "token_number": target["token_number"],
        "patient_code": target["patient_code"],
        "patient_name": target.get("patient_name", "Patient"),
        "room_number": room_number,
        "timestamp": now_iso,
        "status": "ANNOUNCED",
    })

    # Log Audit Event
    get_audit_events_col().insert_one({
        "audit_id": f"AUD-{uuid.uuid4().hex[:10]}",
        "action": "PATIENT_CALLED",
        "resource_type": "queue_entry",
        "resource_id": target["entry_id"],
        "user_id": doctor_name,
        "timestamp": now_iso,
        "details": f"Called Token {target['token_number']} to {room_number}",
    })

    updated = col.find_one({"entry_id": target["entry_id"]})
    cfg = get_queue_config()
    return QueueItemResponse(
        entry_id=updated["entry_id"],
        token_number=updated["token_number"],
        patient_code=updated["patient_code"],
        patient_name=updated["patient_name"],
        encounter_id=updated["encounter_id"],
        department=updated["department"],
        arrival_time=updated["arrival_time"],
        waiting_time_minutes=calculate_waiting_time_mins(updated["arrival_time"]),
        current_position=1,
        recommended_priority=updated.get("recommended_priority", 3),
        clinician_approved_priority=updated.get("clinician_approved_priority", 3),
        queue_status=updated["queue_status"],
        assigned_room=updated.get("assigned_room"),
        is_emergency=updated.get("is_emergency", False),
        is_overridden=updated.get("is_overridden", False),
        override_reason=updated.get("override_reason"),
        active_policy=cfg.get("active_policy", "DYNAMIC_HYBRID"),
        rank_score=0.0,
    )


def transition_queue_status(entry_id: str, new_status: str, actor_id: str) -> QueueItemResponse:
    """Transition queue entry to IN_CONSULTATION, COMPLETED, or CANCELLED."""
    col = get_queue_entries_col()
    target = col.find_one({"entry_id": entry_id})
    if not target:
        raise ValueError(f"Queue entry '{entry_id}' not found.")

    valid_transitions = {
        "WAITING": ["CALLED", "CANCELLED"],
        "CALLED": ["IN_CONSULTATION", "WAITING", "CANCELLED"],
        "IN_CONSULTATION": ["COMPLETED", "CANCELLED"],
    }

    current = target.get("queue_status", "WAITING")
    if new_status not in valid_transitions.get(current, []):
        raise ValueError(f"Invalid transition from '{current}' to '{new_status}'.")

    now_iso = utc_iso_now()
    update_fields = {"queue_status": new_status, "updated_at": now_iso}
    if new_status == "IN_CONSULTATION":
        update_fields["consultation_started_at"] = now_iso
    elif new_status == "COMPLETED":
        update_fields["completed_at"] = now_iso

    col.update_one({"entry_id": entry_id}, {"$set": update_fields})

    get_audit_events_col().insert_one({
        "audit_id": f"AUD-{uuid.uuid4().hex[:10]}",
        "action": f"QUEUE_STATUS_{new_status}",
        "resource_type": "queue_entry",
        "resource_id": entry_id,
        "user_id": actor_id,
        "timestamp": now_iso,
        "details": f"Transitioned entry {entry_id} to {new_status}",
    })

    updated = col.find_one({"entry_id": entry_id})
    cfg = get_queue_config()
    return QueueItemResponse(
        entry_id=updated["entry_id"],
        token_number=updated["token_number"],
        patient_code=updated["patient_code"],
        patient_name=updated["patient_name"],
        encounter_id=updated["encounter_id"],
        department=updated["department"],
        arrival_time=updated["arrival_time"],
        waiting_time_minutes=calculate_waiting_time_mins(updated["arrival_time"]),
        current_position=1,
        recommended_priority=updated.get("recommended_priority", 3),
        clinician_approved_priority=updated.get("clinician_approved_priority", 3),
        queue_status=updated["queue_status"],
        assigned_room=updated.get("assigned_room"),
        is_emergency=updated.get("is_emergency", False),
        is_overridden=updated.get("is_overridden", False),
        override_reason=updated.get("override_reason"),
        active_policy=cfg.get("active_policy", "DYNAMIC_HYBRID"),
        rank_score=0.0,
    )


def apply_doctor_override(
    entry_id: str,
    payload: QueueOverridePayload,
    doctor_id: str,
) -> QueueItemResponse:
    """Doctor manual override of patient priority with mandatory clinical rationale."""
    col = get_queue_entries_col()
    entry = col.find_one({"entry_id": entry_id})
    if not entry:
        raise ValueError(f"Queue entry '{entry_id}' not found.")

    old_priority = entry.get("clinician_approved_priority", 3)
    now_iso = utc_iso_now()

    # Update queue entry
    col.update_one(
        {"entry_id": entry_id},
        {"$set": {
            "clinician_approved_priority": payload.new_priority,
            "is_overridden": True,
            "override_reason": payload.override_reason,
            "overridden_by": doctor_id,
            "overridden_at": now_iso,
        }}
    )

    # Persist immutable doctor override record
    override_id = f"OVR-{uuid.uuid4().hex[:8].upper()}"
    get_doctor_overrides_col().insert_one({
        "override_id": override_id,
        "queue_entry_id": entry_id,
        "encounter_id": entry["encounter_id"],
        "patient_code": entry["patient_code"],
        "doctor_id": doctor_id,
        "previous_priority": old_priority,
        "new_priority": payload.new_priority,
        "override_reason": payload.override_reason,
        "clinical_rationale": payload.clinical_rationale,
        "timestamp": now_iso,
    })

    # Log audit event
    get_audit_events_col().insert_one({
        "audit_id": f"AUD-{uuid.uuid4().hex[:10]}",
        "action": "PRIORITY_OVERRIDDEN",
        "resource_type": "queue_entry",
        "resource_id": entry_id,
        "user_id": doctor_id,
        "timestamp": now_iso,
        "details": f"Priority adjusted from Level {old_priority} to Level {payload.new_priority}. Reason: {payload.override_reason}",
    })

    updated = col.find_one({"entry_id": entry_id})
    cfg = get_queue_config()
    return QueueItemResponse(
        entry_id=updated["entry_id"],
        token_number=updated["token_number"],
        patient_code=updated["patient_code"],
        patient_name=updated["patient_name"],
        encounter_id=updated["encounter_id"],
        department=updated["department"],
        arrival_time=updated["arrival_time"],
        waiting_time_minutes=calculate_waiting_time_mins(updated["arrival_time"]),
        current_position=1,
        recommended_priority=updated.get("recommended_priority", 3),
        clinician_approved_priority=updated.get("clinician_approved_priority", 3),
        queue_status=updated["queue_status"],
        assigned_room=updated.get("assigned_room"),
        is_emergency=updated.get("is_emergency", False),
        is_overridden=True,
        override_reason=payload.override_reason,
        active_policy=cfg.get("active_policy", "DYNAMIC_HYBRID"),
        rank_score=0.0,
    )


def get_queue_severity_summary() -> QueueSeveritySummary:
    """Compute queue counts by priority tier and operational status."""
    col = get_queue_entries_col()
    cfg = get_queue_config()

    cursor = col.find({"queue_status": {"$in": ["WAITING", "CALLED", "IN_CONSULTATION"]}})
    items = list(cursor)

    total_waiting = sum(1 for i in items if i.get("queue_status") == "WAITING")
    total_in_consult = sum(1 for i in items if i.get("queue_status") in ["CALLED", "IN_CONSULTATION"])
    today_completed = col.count_documents({
        "entry_id": {"$regex": f"^Q-{get_today_prefix()}"},
        "queue_status": "COMPLETED",
    })

    return QueueSeveritySummary(
        total_active=len(items),
        total_waiting=total_waiting,
        total_in_consultation=total_in_consult,
        total_completed_today=today_completed,
        critical_count=sum(1 for i in items if i.get("clinician_approved_priority") == 1 or i.get("is_emergency")),
        emergent_count=sum(1 for i in items if i.get("clinician_approved_priority") == 2 and not i.get("is_emergency")),
        urgent_count=sum(1 for i in items if i.get("clinician_approved_priority") == 3 and not i.get("is_emergency")),
        less_urgent_count=sum(1 for i in items if i.get("clinician_approved_priority") == 4),
        non_urgent_count=sum(1 for i in items if i.get("clinician_approved_priority") == 5),
        active_policy=cfg.get("active_policy", "DYNAMIC_HYBRID"),
    )
