# System Limitations, Clinical Risks & Assumptions Log

## 1. Clinical Validity & Domain Transfer Limitations

1. **Emergency Department Acuity vs. Outpatient Department Urgency**:
   - The primary dataset (`triagegeist`) is derived from hospital Emergency Department (ED) triage data using the 5-level Emergency Severity Index (ESI).
   - In an outpatient clinic (OPD), patients rarely present in acute cardiac arrest or respiratory failure (Level 1). Instead, OPD prioritizes sub-acute clinical deterioration, chronic disease exacerbation (e.g., uncontrolled hypertension, diabetic foot infection), and diagnostic workup urgency.
   - **Mitigation**: The system explicitly operates as a *decision-support tool*, never an autonomous triage officer. Clinicians hold exclusive authority over consultation order and treatment decisions.

2. **Absence of True Multi-Visit Longitudinal Trajectories in Raw Data**:
   - As established in the dataset audit, `triagegeist` contains exactly one row per patient in `train.csv` (80,000 unique patients) with static comorbidity flags in `patient_history.csv`.
   - It does not contain genuine multi-year time-series vitals for the same individual.
   - **Mitigation**: Multi-encounter outpatient visits are modeled using realistic clinical simulation profiles and verified EHR structures in MongoDB.

---

## 2. Machine Learning & Inference Limitations

1. **Class Imbalance & Under-Triage Risk**:
   - Level 1 (immediate resuscitation) comprises only 4.03% of the dataset, whereas Level 3 (urgent) comprises 36.15%. Standard unweighted loss functions can result in dangerous under-triage of rare, critical presentations.
   - **Mitigation**: An independent rule-based emergency pathway executes synchronously *before* ML inference, ensuring life-threatening vitals trigger immediate clinical escalation regardless of model probability output.

2. **Data Leakage Risk (Post-Arrival Variables)**:
   - In `triagegeist`, `disposition` (e.g. admitted, deceased) and `ed_los_hours` correlate heavily with acuity (-0.757 correlation). These variables represent clinical events occurring hours *after* triage.
   - **Mitigation**: Both fields are strictly blacklisted from the model training and inference pipelines.

3. **Handling of Missing Physiological Measurements**:
   - Missing vital signs occur in real clinical workflows (e.g., blood pressure unmeasured in 5.18% of cases).
   - **Hazard**: Silently substituting standard normal vitals (e.g., BP 120/80) masks patient deterioration.
   - **Mitigation**: Explicit binary missingness indicator features (`systolic_bp_missing = 1`) are fed to models alongside median imputation, preserving the clinical signal of unmeasured vitals.

---

## 3. OCR & Document Processing Limitations

1. **Handwriting & Poor Scans**:
   - Handwritten doctor prescriptions and low-resolution mobile photographs suffer significant OCR word error rates (WER).
   - **Hazard**: Converting an OCR misread (e.g., "50mg" read as "500mg") directly into verified medical history risks catastrophic clinical medication errors.
   - **Mitigation**: Zero automated diagnosis promotion. Every OCR output requires explicit human staff review and verification before being committed to `medical_history`.

---

## 4. LLM Doctor Assistant Limitations

1. **Hallucination & Clinical Extrapolation**:
   - Large Language Models can fabricate lab values or assume chronic diseases not present in the record.
   - **Mitigation**: The LLM prompt is strictly constrained to source-grounded facts extracted from the active encounter and verified history. An offline deterministic fallback summarizer is provided for zero-dependency execution.
   - Summaries are presented in an editable container requiring doctor review before appending to consultation notes.

---

## 5. Queue Policy & Starvation Dynamics

1. **Low-Acuity Starvation Under Pure Priority Queuing**:
   - Under standard priority queuing (Policy B), an influx of Level 2 and Level 3 patients can cause Level 4 and Level 5 patients to wait indefinitely.
   - **Mitigation**: The Proposed Dynamic Hybrid Policy (Policy C) integrates waiting-time aging safeguards: as waiting duration approaches clinically safe limits, patient rank score increases, guaranteeing service within bounded maximum wait thresholds.
