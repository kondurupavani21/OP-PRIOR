"""Business logic and services package."""
from app.services.triage_service import calculate_triage_priority
from app.services.patient_service import (
    create_patient,
    get_patient_by_code,
    get_patients_list,
    update_patient_record,
    add_patient_visit,
)
from app.services.queue_service import (
    add_to_queue,
    get_active_queue,
    update_queue_status,
    call_next_patient,
    get_queue_summary,
)
from app.services.consultation_service import (
    create_consultation,
    get_consultations_by_patient,
    list_recent_consultations,
)
from app.services.auth_service import (
    create_user,
    authenticate_user,
    get_user_by_email,
)

__all__ = [
    "calculate_triage_priority",
    "create_patient",
    "get_patient_by_code",
    "get_patients_list",
    "update_patient_record",
    "add_patient_visit",
    "add_to_queue",
    "get_active_queue",
    "update_queue_status",
    "call_next_patient",
    "get_queue_summary",
    "create_consultation",
    "get_consultations_by_patient",
    "list_recent_consultations",
    "create_user",
    "authenticate_user",
    "get_user_by_email",
]
