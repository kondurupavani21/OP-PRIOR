# Implementation Plan & Phase Milestones

## Phase Roadmap & Completion Criteria

### Phase 1: Audit, Datasets & Safety Architecture (COMPLETED)
- [x] Inspect existing React frontend, components, and SQLite backend.
- [x] Unpack and audit `triagegeist` and `Hospital ER_Data.csv`.
- [x] Document dataset schemas, distributions, class imbalance, and missingness in `docs/dataset_audit.md`.
- [x] Formulate system architecture in `docs/architecture.md`.
- [x] Establish functional requirements & safety checklist in `docs/requirements.md`.
- [x] Formulate risks and limitations log in `docs/limitations.md`.
- **Completion Criterion**: Audits verified, documentation persisted, git working tree clean.

---

### Phase 2: Core React + FastAPI + MongoDB Foundation (CURRENT MILESTONE)
- [ ] Create resilient MongoDB database layer (`backend/app/db/mongodb.py`) supporting real MongoDB URI and automated in-memory `mongomock` fallback.
- [ ] Initialize all 12 MongoDB collection schemas and indexes.
- [ ] Implement Patient and Encounter Pydantic schemas and REST endpoints:
  - `POST /api/v1/patients` (Register patient with verified identity check)
  - `GET /api/v1/patients` (Search by phone, name, or ID)
  - `GET /api/v1/patients/{patient_id}` (Retrieve profile & encounters)
  - `POST /api/v1/encounters` (Record visit vitals, symptoms, and execute Emergency Warning Screening)
  - `GET /api/v1/encounters/{encounter_id}`
  - `GET /api/v1/patients/{patient_id}/encounters`
- [ ] Implement the Synchronous Emergency Screening Engine:
  - Flags severe hypoxia, hypertensive crisis, shock risk, severe tachycardia/bradycardia, altered mental status.
- [ ] Write automated Pytest suite for patient and encounter workflows (`backend/tests/test_patients_encounters.py`).
- [ ] Connect React frontend `PatientRegistration.jsx` to backend endpoints via `src/services/api.js`.
- **Completion Criterion**: Automated Pytest passes 100%, patient registration persists to MongoDB collections, emergency vitals trigger prominent escalation alert.

---

### Phase 3: Medical History & Document OCR Verification Workflow
- [ ] Implement document upload endpoint `POST /api/v1/documents/upload`.
- [ ] Implement OCR extraction service with Tesseract / rule-based fallback.
- [ ] Human verification review endpoint `PATCH /api/v1/documents/{document_id}/verification`.
- [ ] Store verified historical diagnoses in `medical_history` collection.
- [ ] Display verified records and documents in `PatientDetails.jsx` and `PatientHistory.jsx`.
- **Completion Criterion**: Document uploaded, extracted fields reviewed and confirmed by staff, committed to verified medical history without unreviewed auto-promotion.

---

### Phase 4: Doctor Dashboard & Queue Management Engine
- [ ] Implement Queue REST endpoints:
  - `GET /api/v1/queue` (Ordered by selected policy: FCFS, Priority, or Proposed Hybrid C)
  - `POST /api/v1/queue` (Enqueue encounter)
  - `POST /api/v1/queue/{entry_id}/call`
  - `POST /api/v1/queue/{entry_id}/override` (Mandatory clinical rationale)
  - `POST /api/v1/queue/{entry_id}/complete`
- [ ] Connect Doctor Dashboard with live queue, patient-detail drawer, and override modal.
- [ ] Implement audit logging for every queue transition and override.
- **Completion Criterion**: Doctor can call, view, and override queue order with logged justifications and dynamic reordering.

---

### Phase 5: Machine Learning Models & Experimental Evaluation
- [ ] Extract clean feature matrix from `triagegeist/train.csv` (excluding post-arrival `disposition` and `ed_los_hours`).
- [ ] Train Model A (Current-visit features only) vs Model B (Current-visit + verified historical comorbidity indicators).
- [ ] Train baseline Logistic Regression and Random Forest classifiers.
- [ ] Evaluate Macro F1, Balanced Accuracy, per-class precision/recall, and calibration.
- [ ] Persist trained pipeline with Joblib in `models/`.
- **Completion Criterion**: Model pipeline saved, evaluation report and confusion matrix generated.

---

### Phase 6: Neural Network (MLP) Comparison
- [ ] Train Multi-Layer Perceptron (MLP) neural network.
- [ ] Compare MLP vs Random Forest and Logistic Regression on held-out validation set.
- [ ] Document class-specific performance and under-triage rate for critical Level 1 cases.
- **Completion Criterion**: Model card generated in `docs/model_card.md` comparing all architectures.

---

### Phase 7: LLM Doctor Assistant & Grounded Summaries
- [ ] Build provider-independent LLM adapter interface supporting Mock and OpenAI/Ollama APIs.
- [ ] Implement prompt template grounding summaries strictly in current visit and verified history.
- [ ] Provide doctor review, editing, and approval workflow.
- **Completion Criterion**: Structured clinical summary generated with source citations; works reliably in offline mock mode.

---

### Phase 8: Bilingual Voice Announcements & Waiting Room Display
- [ ] Implement dedicated public waiting display route `/waiting-room`.
- [ ] Implement Web Speech API announcement in English and Telugu.
- [ ] Implement event-based duplicate prevention and visual on-screen fallback.
- **Completion Criterion**: Token call triggers single speech announcement and on-screen card without duplicate playback.

---

### Phase 9: Conference Simulation Engine
- [ ] Implement Monte Carlo OPD Queue Simulation engine (`backend/app/simulation/queue_sim.py`).
- [ ] Compare Policy A (FCFS), Policy B (Conventional Priority), and Policy C (Dynamic Hybrid).
- [ ] Compute mean wait, 95th percentile wait, max wait, throughput, and starvation metrics across multiple seeds.
- [ ] Generate research summary charts and result tables.
- **Completion Criterion**: Reproducible simulation script runs, outputting publication-ready comparative metric tables.

---

### Phase 10: System Integration, Security Audit & Research Release
- [ ] End-to-end integration testing across frontend, backend, and database.
- [ ] Complete `README.md` and documentation suite.
- [ ] Verify clean demo workflow.
- **Completion Criterion**: All tests passing, full system runnable with single startup command.
