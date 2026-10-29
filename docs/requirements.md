# System Requirements & Clinical Safety Specification

## 1. User Roles & Authorization Matrix

| Capability / Action | Receptionist | Doctor | Administrator | Unauthenticated |
| :--- | :---: | :---: | :---: | :---: |
| Search / Verify Patient Identity | Yes | Yes | Yes | No |
| Register New Patient Profile | Yes | Yes | Yes | No |
| Record Intake Vitals & Symptoms | Yes | Yes | Yes | No |
| Upload Patient Medical Documents | Yes | Yes | Yes | No |
| Review / Verify OCR Extracted Records | Yes | Yes | Yes | No |
| Add Patient to Active Waiting Queue | Yes | Yes | Yes | No |
| View Active Waiting Queue (Full Clinical Detail) | No (Tokens only) | Yes | Yes | No |
| View Public Waiting Display (Token + Room) | Yes | Yes | Yes | Yes |
| Inspect AI Clinical Summary & Source Citations | No | Yes | Yes | No |
| Edit & Approve AI Clinical Summary | No | Yes | Yes | No |
| Call Next Patient into Consultation | No | Yes | Yes | No |
| Override Queue Order / Acuity Tier | No | Yes | Yes | No |
| Complete Consultation & Record Notes | No | Yes | Yes | No |
| Configure Queue Policies & Waiting Safeguards | No | No | Yes | No |
| Trigger Simulation Benchmarking Experiments | No | No | Yes | No |
| Inspect Immutable Security Audit Logs | No | No | Yes | No |

---

## 2. Functional Requirements Checklist

### 2.1 Patient Registration & Identity Matching
- [x] **FR-1.1 Unique Patient Identification**: Automatically assign deterministic, human-readable patient codes (e.g. `PAT-1001`).
- [x] **FR-1.2 Verified Identity Matching**: Search by normalized phone number and full name to prevent duplicate creation while avoiding accidental identity merging.
- [x] **FR-1.3 New vs. Returning Support**: Explicitly distinguish first-time patients (zero prior history) from returning patients (linked prior visits).
- [x] **FR-1.4 No History Penalty**: Ensure new patients without historical documents are fully assessed on current presenting vitals without penalty.
- [x] **FR-1.5 Comprehensive Clinical Intake**: Collect chief complaint, structured organ system category, duration, pain score, temperature, heart rate, blood pressure, respiratory rate, and SpO2.
- [x] **FR-1.6 Missingness Representation**: Explicitly record missing vitals as missing rather than silently imputing normal physiological values.

### 2.2 Clinical Safety & Emergency Screening Pathway
- [x] **FR-2.1 Synchronous Emergency Detection**: Rule-based screening executes synchronously during intake:
  - Severe Hypoxia ($SpO_2 < 90\%$)
  - Hypertensive Crisis ($SBP \ge 180 \text{ mmHg}$ or $DBP \ge 110 \text{ mmHg}$)
  - Hypotensive Shock Risk ($SBP < 90 \text{ mmHg}$)
  - Extreme Tachycardia ($HR > 130 \text{ bpm}$) or Bradycardia ($HR < 45 \text{ bpm}$)
  - Altered Mental Status / Severe Respiratory Distress ($RR > 32$ or $< 10$)
- [x] **FR-2.2 Immediate Visual Escalation**: Prominently display red alert banner with explicit instructions to transfer patient to emergency resuscitation immediately.
- [x] **FR-2.3 No AI Blocking**: Emergency warning pathway does NOT wait for OCR completion, neural network inference, or LLM generation.

### 2.3 Previous Consultations & Medical Document Processing
- [x] **FR-3.1 Previous Consultation Inquiry**: Mandatory inquiry during patient registration: *"Have you consulted another doctor or hospital for this current problem? (Yes / No / Not sure)"*.
- [x] **FR-3.2 Multi-Entry Previous Visits**: Collect hospital/doctor, consultation date, symptoms reported, diagnosis given, investigations done, treatment prescribed, medicines taken, duration, response (Improved / Unchanged / Worsened), and side effects.
- [x] **FR-3.3 Dual-Engine Document Intake**: Accept PDF (direct text via `pypdf`), images (PNG, JPEG via Tesseract OCR fallback), and text files across 7 categories (Prescription, Lab Report, Radiology Report, Discharge Summary, Clinical Note, EMR Export, Other).
- [x] **FR-3.4 Patient Identity Matching Check**: Cross-check extracted patient name against registered profile with 3 explicit states (`MATCHED`, `UNCERTAIN`, `MISMATCH`) requiring human confirmation before acceptance.
- [x] **FR-3.5 Laboratory & Medication Structured Parsing**: Automatically extract test names, numerical values, units, reference ranges, abnormal flags (e.g., HbA1c > 5.6%, Fasting Sugar > 99 mg/dL), and medications with uncertainty scores.
- [x] **FR-3.6 Human Verification Checkpoint**: Staff verify extracted diagnoses, medications, and labs before committing to immutable `medical_history` with source provenance.
- [x] **FR-3.7 Upload Security & Size Constraints**: Enforce strict MIME verification and configurable file size limits (`MAX_UPLOAD_SIZE_MB`, default 15MB) returning HTTP 413 on oversized files.

### 2.4 Grounded AI Clinical Summary & Doctor Decision-Support
- [x] **FR-4.1 7-Section Grounded Clinical Summary**:
  - **Section A**: Current Presentation & Objective Vitals Assessment (including vital omissions).
  - **Section B**: Previous Consultations for this Problem (facilities, treatments, responses).
  - **Section C**: Previous Investigations & Abnormal Lab Findings.
  - **Section D**: Relevant Medical History & Active Verified Medications.
  - **Section E**: Chronological Clinical Timeline.
  - **Section F**: Important Clinical Uncertainties & Missing Records.
  - **Section G**: Traceable Source Citations (`[VITALS]`, `[PREVIOUS_CONSULTATION]`, `[LAB_REPORT]`, `[PRESCRIPTION]`).
- [x] **FR-4.2 Resilient Multi-Provider Architecture**: Configurable live OpenAI and Ollama integrations with a 100% offline deterministic rule-based grounded fallback.
- [x] **FR-4.3 Staleness Detection & Regeneration**: Automatically detect when newly uploaded documents or consultation notes invalidate existing summaries (`is_stale == True`) with one-click doctor regeneration.
- [x] **FR-4.4 Doctor Review Governance**: 5-section review workflow integrated directly in Doctor Dashboard and Consultation Desk with formal status (`PENDING_REVIEW`, `ACCEPTED`, `EDITED`, `REJECTED`).
- [x] **FR-4.5 Emergency Screening Independence**: Emergency triage runs synchronously on intake vitals and chief complaints without blocking on document uploads, OCR, or LLM generation.

### 2.5 Conference Simulation & Research Evaluation
- [x] **FR-5.1 Policy Benchmarking**: Compare FCFS, Conventional Priority Queue, and Proposed Dynamic Hybrid Policy under identical synthetic arrival streams.
- [x] **FR-5.2 Quantitative Metrics**: Compute mean, median, 90th percentile, and max waiting time; throughput per hour; and starvation rates by acuity tier.
- [x] **FR-5.3 Reproducibility**: Seeded random generation for repeatable experiments.

---

## 3. Non-Functional Requirements

- **NFR-1 Response Time**: API intake and emergency check response latency $< 150 \text{ ms}$.
- **NFR-2 Resilient Database**: PyMongo connection with automated `mongomock` in-memory fallback for immediate zero-setup execution.
- **NFR-3 Security**: Role-based access control, JWT authentication, no API keys or PHI in frontend bundles.
- **NFR-4 Usability**: Accessible UI adhering to clinical contrast standards, legible typography, and no reliance on color alone for urgency indicators.
