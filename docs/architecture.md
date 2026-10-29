# System Architecture & Technical Specification

## 1. High-Level Architectural Overview

The AI-Assisted Outpatient Department (OPD) Patient Prioritization and Doctor Decision-Support System is organized as a decoupled, multi-tier clinical micro-service architecture:

```
[ Receptionist Workstation ]       [ Doctor Consultation Room ]      [ Waiting Room Display ]
          │                                      │                               │
          │ (React 19 + Vite SPA)                │ (Doctor Dashboard)            │ (Web Speech API Display)
          └───────────────────┬──────────────────┴───────────────────────────────┘
                              │ HTTPS / REST JSON APIs
                              ▼
        ┌─────────────────────────────────────────────────────────┐
        │                 FastAPI Application Server               │
        │  ├── Core Middleware (CORS, JWT Auth, Audit Logger)    │
        │  ├── Clinical Domain Routers:                           │
        │  │    /patients, /encounters, /queue, /documents        │
        │  │    /assessments, /summaries, /simulations, /auth     │
        │  ├── Business Logic Services & Domain Engines           │
        │  │    ├── Emergency Screening Rule Engine (Rule-based)   │
        │  │    ├── Prioritization Engine (Hybrid Policy C)        │
        │  │    ├── ML Inference Engine (Model A/B/C/D)           │
        │  │    ├── OCR Engine & Verification Pipeline            │
        │  │    ├── LLM Adapter Interface (Grounded Summaries)    │
        │  │    └── Monte Carlo OPD Queue Simulation Engine        │
        └────────────────────────────┬────────────────────────────┘
                                     │
           ┌─────────────────────────┴─────────────────────────┐
           ▼                                                   ▼
┌───────────────────────────────┐               ┌───────────────────────────────┐
│        MongoDB Primary        │               │      Saved Model Artifacts    │
│  (PyMongo / Motor with        │               │  - Preprocessing Pipelines    │
│   mongomock resilient adapter)│               │  - Logistic / RF / MLP Models │
│  - 12 Dedicated Collections   │               │  - Joblib & PyTorch Weights   │
└───────────────────────────────┘               └───────────────────────────────┘
```

---

## 2. Component Responsibilities & Boundaries

### 2.1 Frontend Tier (`src/`)
- Built on **React 19 + Vite** with client-side routing via **React Router v7**.
- Modular components:
  - `pages/PatientRegistration.jsx`: Comprehensive intake for demographic, symptom, vitals, and historical document upload.
  - `pages/DoctorDashboard.jsx`: Doctor queue management, active consultation panel, AI recommendation review, and manual override dialog with required justification.
  - `pages/PriorityQueue.jsx`: Live triage queue with severity badges, waiting time trackers, and policy inspection.
  - `pages/Consultation.jsx`: In-consultation doctor workspace with longitudinal trends and editable AI clinical summaries.
  - `pages/WaitingRoomDisplay.jsx`: Public display with token numbers, consultation room calls, and multi-lingual voice announcements.
  - `pages/SimulationDashboard.jsx`: Conference research simulation runner and comparative policy benchmark visualizer.

### 2.2 Backend Tier (`backend/app/`)
- **FastAPI Framework** with asynchronous handlers and Pydantic v2 validation.
- **Resilient Database Layer**: Native MongoDB connection with `mongomock` in-memory fallback for immediate zero-config developer execution without needing an external daemon.
- **Clinical Safety Separation**:
  - Independent Emergency Screening Pathway executes *synchronously* before any ML inference or LLM processing.
  - AI predictions are labeled as *recommendations*; clinician approvals and overrides are strictly tracked.
- **Provider-Independent LLM Adapter**: Supports mock summarization (zero external API dependency) and OpenAI/Anthropic/Ollama compatible endpoints via environment configuration.
- **OCR Engine Interface**: Pluggable architecture supporting Tesseract, PaddleOCR, and rule-based document parsing with manual review checkpoints.

---

## 3. MongoDB Database Architecture

The application defines 12 distinct MongoDB collections designed for referential stability without storing bloated copies of clinical history inside queue entries:

### 3.1 Collections & Indexing Strategy

1. **`users`**
   - Stores staff and clinician accounts, hashed credentials, and role-based permissions (`Receptionist`, `Doctor`, `Administrator`).
   - *Indexes*: Unique index on `email`, index on `role`.

2. **`patients`**
   - Core demographic and master patient identity.
   - *Fields*: `patient_code` (unique human-readable ID like `PAT-1001`), `full_name`, `age`, `gender`, `contact`, `emergency_contact`, `preferred_language`, `accessibility_needs`, `identity_verification_status`, `created_at`, `updated_at`.
   - *Indexes*: Unique index on `patient_code`, compound index on `contact` and `full_name`.

3. **`encounters`**
   - Each clinic visit creates an encounter record linked to a `patient_id`.
   - *Fields*: `encounter_id`, `patient_id`, `department`, `arrival_time`, `visit_type` (`NEW` vs `RETURNING`), `chief_complaint`, `complaint_category`, `symptom_duration`, `symptom_findings`, `vital_signs` (temperature, heart_rate, respiratory_rate, systolic_bp, diastolic_bp, spo2, blood_sugar, pain_score), `missingness_indicators`, `emergency_flags`, `status`.
   - *Indexes*: Index on `patient_id`, index on `arrival_time`, index on `status`.

4. **`medical_documents`**
   - Tracks uploaded patient prescriptions, lab reports, and external discharge summaries.
   - *Fields*: `document_id`, `patient_id`, `encounter_id`, `document_type`, `document_date`, `upload_timestamp`, `file_path`, `ocr_engine`, `extracted_text`, `extracted_fields`, `verification_status` (`PENDING_REVIEW`, `VERIFIED`, `REJECTED`), `reviewer_id`, `reviewed_at`.
   - *Indexes*: Index on `patient_id`, index on `verification_status`.

5. **`medical_history`**
   - Verified longitudinal patient conditions, past surgeries, chronic illnesses, and allergies.
   - *Fields*: `history_id`, `patient_id`, `condition_name`, `condition_system`, `diagnosed_date`, `status` (`ACTIVE`, `RESOLVED`), `source_type` (`PATIENT_REPORTED`, `OCR_DOCUMENT`, `PREVIOUS_ENCOUNTER`), `source_document_id`, `verification_status`.
   - *Indexes*: Compound index on `patient_id` and `condition_name`.

6. **`triage_assessments`**
   - Stores ML model outputs and clinical rule evaluations for an encounter.
   - *Fields*: `assessment_id`, `encounter_id`, `patient_id`, `model_version`, `model_eligibility`, `predicted_priority` (1 to 5), `class_probabilities`, `contributing_factors`, `missing_input_flags`, `emergency_escalation_triggered`, `calculated_at`.
   - *Indexes*: Index on `encounter_id`.

7. **`queue_entries`**
   - Live waiting queue tokens.
   - *Fields*: `entry_id`, `token_number`, `encounter_id`, `patient_id`, `patient_code`, `department`, `arrival_time`, `recommended_priority`, `clinician_approved_priority`, `queue_status` (`WAITING`, `WITH_DOCTOR`, `COMPLETED`, `CANCELLED`), `waiting_time_minutes`, `current_position`, `last_called_at`, `assigned_room`.
   - *Indexes*: Unique index on `token_number` (daily scope), index on `queue_status`, compound index on `clinician_approved_priority` and `arrival_time`.

8. **`doctor_overrides`**
   - Audit trail of clinician queue re-orderings or priority changes.
   - *Fields*: `override_id`, `queue_entry_id`, `encounter_id`, `doctor_id`, `previous_priority`, `new_priority`, `previous_position`, `new_position`, `override_reason`, `clinical_rationale`, `timestamp`.
   - *Indexes*: Index on `doctor_id`, index on `queue_entry_id`.

9. **`ai_summaries`**
   - Source-grounded clinical summaries generated by the LLM assistant.
   - *Fields*: `summary_id`, `encounter_id`, `patient_id`, `current_visit_summary`, `relevant_history_summary`, `vital_signs_summary`, `medication_allergies_summary`, `missing_information_notice`, `source_references`, `model_provider`, `generated_at`, `doctor_review_status` (`UNREVIEWED`, `APPROVED`, `EDITED`), `doctor_edited_summary`.
   - *Indexes*: Unique index on `encounter_id`.

10. **`model_predictions`**
    - Machine learning telemetry for performance monitoring, drift detection, and research audit.
    - *Fields*: `prediction_id`, `model_id`, `model_type` (`LOGISTIC_REGRESSION`, `RANDOM_FOREST`, `MLP`), `input_vector_summary`, `predicted_class`, `latency_ms`, `created_at`.

11. **`announcement_events`**
    - Log of voice and visual queue token calls to prevent double-announcements.
    - *Fields*: `event_id`, `token_number`, `room_number`, `language` (`en`, `te`), `status` (`PLAYED`, `FALLBACK_SHOWN`), `triggered_by_user_id`, `timestamp`.

12. **`audit_events`**
    - Immutable operational audit log capturing user actions, PHI access, role alterations, and queue interventions.
    - *Fields*: `audit_id`, `user_id`, `user_role`, `action`, `resource_type`, `resource_id`, `ip_address`, `timestamp`, `details`.
    - *Indexes*: Index on `timestamp`, index on `user_id`.

---

## 4. Prioritization Policy Architecture

The queue engine supports 3 distinct, configurable policies evaluated during research:

1. **Policy A: First-Come, First-Served (FCFS Baseline)**
   - Ordering: Chronological order of `arrival_time`.
   - Safety Exception: Immediate emergency cases flagged by rule-based escalation bypass standard queue directly to emergency care.

2. **Policy B: Conventional Priority Queue**
   - Ordering: Strict ordering by discrete triage priority tiers (Level 1 > Level 2 > Level 3 > Level 4 > Level 5), ordered by arrival time within each tier.
   - Limitation: Subject to low-priority patient starvation under heavy loads.

3. **Policy C: Proposed Dynamic Hybrid Policy**
   - Ordering Formula:
     $$\text{Rank Score} = w_p \cdot \text{PriorityWeight}(P) + w_w \cdot \min\left(\frac{T_{\text{wait}}}{T_{\text{max\_safe}}}, 1.5\right) + \text{EmergencyBonus} + \text{DoctorOverrideDelta}$$
   - Waiting-Time Safeguard: Prevents lower-acuity patients (Levels 4 and 5) from starving by progressively aging their effective queue priority as waiting time exceeds clinically safe thresholds.
   - Doctor In-The-Loop: Clinician override immediately supersedes algorithmic rank, with persistent audit logging.

---

## 5. Security & Privacy Boundaries

- **Role-Based Authorization (RBAC)**: Enforced via FastAPI JWT dependencies (`require_doctor`, `require_receptionist`, `require_admin`).
- **PII Separation**: Public waiting room screens and announcement engines never receive patient names, diagnoses, or symptoms. Only `token_number` and `room_number` are exposed.
- **Safe Secrets Handling**: Provider API keys and database credentials reside exclusively in server-side environment variables (`backend/.env`).
- **Resilient Fallback Mode**: Core patient registration and queue operations remain 100% operational even if LLM APIs or ML models are offline.
