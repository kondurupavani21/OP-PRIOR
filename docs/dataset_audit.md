# Clinical Dataset Audit & Provenance Report

## 1. Executive Summary & Research Scope

This document provides a thorough audit of the two candidate datasets available for the AI-Assisted Outpatient Department (OPD) Patient Prioritization & Doctor Decision-Support System:
1. **Dataset A (`triagegeist`)**: Clinical emergency triage acuity records from Kaggle Triagegeist (`train.csv`, `test.csv`, `patient_history.csv`, `chief_complaints.csv`, `sample_submission.csv`).
2. **Dataset B (`Hospital ER_Data.csv`)**: Operational hospital emergency room administrative records (9,216 patient visits).

### Key Clinical & Informatics Findings
- **Target Suitability**: `triagegeist` provides an explicit clinical target: `triage_acuity` ranging from 1 (immediate/resuscitation) to 5 (non-urgent), matching the 5-level Emergency Severity Index (ESI) triage standard. However, **emergency-department acuity is not identical to outpatient queue urgency**. OPD patients rarely present as Level 1 (immediate cardiac arrest/apnea); outpatient clinics manage semi-urgent or non-urgent presentations with chronic comorbidity decompensation.
- **Data Leakage Safeguards**: In `triagegeist/train.csv`, columns `disposition` (e.g. admitted, deceased) and `ed_los_hours` (length of stay) represent post-arrival outcomes that correlate strongly with acuity (-0.757 correlation for length of stay). **These must be strictly excluded from model feature sets** to avoid future information leakage.
- **Longitudinal Record Reality**: In `triagegeist`, each `patient_id` appears exactly once in `train.csv` (80,000 unique patients) and once in `test.csv` (20,000 unique patients). There is **zero patient overlap** across splits. The accompanying `patient_history.csv` provides static comorbidity indicator flags (25 binary fields) rather than multi-encounter longitudinal time series. True multi-visit outpatient trajectories are simulated or supplemented with verified clinical workflows.
- **Dataset B Operational Role**: `Hospital ER_Data.csv` contains operational wait times (10–60 min), gender, age, race, and admission flags, but **lacks all clinical vitals, chief complaints, and triage acuity labels**. It cannot be used to train a clinical acuity model, but serves as an empirical empirical prior for queue waiting-time benchmarking and arrival rate simulations.

---

## 2. Dataset A: Triagegeist Detailed Audit

### 2.1 File Inventory & Dimensionality

| File | Rows | Columns | Unique Patients | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `train.csv` | 80,000 | 40 | 80,000 | Primary training set with target `triage_acuity` |
| `test.csv` | 20,000 | 37 | 20,000 | Hold-out competition test set (no target) |
| `patient_history.csv` | 100,000 | 26 | 100,000 | Comorbidity flags (1:1 link to train + test) |
| `chief_complaints.csv` | 100,000 | 3 | 100,000 | Raw unstructured complaint text & organ system |
| `sample_submission.csv` | 20,000 | 2 | 20,000 | Benchmark prediction format |

### 2.2 Target Variable Distribution (`triage_acuity` in `train.csv`)

| Acuity Level | Clinical Interpretation (ESI Equivalent) | Count | Percentage | Research Handling |
| :--- | :--- | :--- | :--- | :--- |
| **Level 1** | Resuscitation / Immediate life threat | 3,222 | 4.03% | Severe class imbalance; emergency safety pathway bypass |
| **Level 2** | Emergent / High risk / Severe pain | 13,439 | 16.80% | Clinically high priority; prioritized over general queue |
| **Level 3** | Urgent / Moderate resource needs | 28,921 | 36.15% | Majority class; standard clinical prioritization |
| **Level 4** | Less Urgent / Single resource need | 23,020 | 28.78% | Standard outpatient queue |
| **Level 5** | Non-urgent / Prescription refill/checkup | 11,398 | 14.25% | Low clinical urgency; prone to starvation without wait safeguards |
| **Total** | | 80,000 | 100.0% | Stratified train/val/test split required |

### 2.3 Column Names, Data Types & Missingness (`train.csv`)

| Column Name | Data Type | Null Count | Null % | Plausible Range / Values | Observed Distribution |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `patient_id` | `object` (str) | 0 | 0.00% | Alphanumeric ID (`TG-XXXX`) | 80,000 unique |
| `site_id` | `object` (str) | 0 | 0.00% | Facility code | 1 site (`SITE-TMP-01`) |
| `triage_nurse_id` | `object` (str) | 0 | 0.00% | Nurse identifier | 60 unique nurses |
| `arrival_mode` | `object` (str) | 0 | 0.00% | `walk-in`, `ambulance`, etc. | Walk-in (72%), Ambulance (28%) |
| `arrival_hour` | `int64` | 0 | 0.00% | 0–23 | Peak 10:00–18:00 |
| `arrival_day` | `object` (str) | 0 | 0.00% | Day of week | Monday through Sunday |
| `arrival_month` | `int64` | 0 | 0.00% | 1–12 | Uniform seasonal spread |
| `arrival_season` | `object` (str) | 0 | 0.00% | `spring`, `summer`, `autumn`, `winter` | Balanced |
| `shift` | `object` (str) | 0 | 0.00% | `morning`, `afternoon`, `night` | Morning (45%), Afternoon (40%), Night (15%) |
| `age` | `int64` | 0 | 0.00% | 18–105 | Min 18, Median 52, Max 102 |
| `age_group` | `object` (str) | 0 | 0.00% | Categorical age bands | `young_adult`, `middle_aged`, `elderly`, `very_elderly` |
| `sex` | `object` (str) | 0 | 0.00% | `M`, `F`, `Other` | F (51.2%), M (48.8%) |
| `language` | `object` (str) | 0 | 0.00% | Primary language | English (81%), Spanish (10%), Other (9%) |
| `insurance_type` | `object` (str) | 0 | 0.00% | `private`, `public`, `uninsured` | Public (48%), Private (42%), Uninsured (10%) |
| `transport_origin` | `object` (str) | 0 | 0.00% | Home, nursing home, public space | Home (78%) |
| `pain_location` | `object` (str) | 0 | 0.00% | Anatomical site | Chest, abdomen, head, back, none |
| `mental_status_triage` | `object` (str) | 0 | 0.00% | Alert, confused, lethargic, unresponsive | Alert (84.1%), Confused (10.2%), Lethargic (4.5%), Unresponsive (1.2%) |
| `chief_complaint_system` | `object` (str) | 0 | 0.00% | Organ system | Respiratory, Cardiac, GI, Neuro, Musculoskeletal |
| `num_prior_ed_visits_12m` | `int64` | 0 | 0.00% | 0–25 | Median 1, Max 18 |
| `num_prior_admissions_12m` | `int64` | 0 | 0.00% | 0–15 | Median 0, Max 12 |
| `num_active_medications` | `int64` | 0 | 0.00% | 0–30 | Median 4, Max 28 |
| `num_comorbidities` | `int64` | 0 | 0.00% | 0–15 | Median 2, Max 14 |
| `systolic_bp` | `float64` | 4,146 | 5.18% | 40.0–260.0 mmHg | Min 40.0, Median 123.1, Max 226.9 |
| `diastolic_bp` | `float64` | 4,146 | 5.18% | 20.0–160.0 mmHg | Min 20.0, Median 75.3, Max 134.8 |
| `mean_arterial_pressure` | `float64` | 4,146 | 5.18% | 30.0–180.0 mmHg | Min 31.2, Median 91.2, Max 165.5 |
| `pulse_pressure` | `float64` | 4,146 | 5.18% | -10.0 to 120.0 mmHg | Min -12.4 (measurement artifact), Median 47.8, Max 118.2 |
| `heart_rate` | `float64` | 0 | 0.00% | 30.0–220.0 bpm | Min 30.0, Median 89.6, Max 207.7 |
| `respiratory_rate` | `float64` | 3,067 | 3.83% | 8.0–60.0 breaths/min | Min 8.0, Median 17.3, Max 51.5 |
| `temperature_c` | `float64` | 574 | 0.72% | 34.0–43.0 °C | Min 35.1, Median 37.5, Max 41.8 |
| `spo2` | `float64` | 0 | 0.00% | 50.0–100.0 % | Min 60.4, Median 97.0, Max 100.0 |
| `gcs_total` | `int64` | 0 | 0.00% | 3–15 | Min 3, Median 15, Max 15 |
| `pain_score` | `int64` | 0 | 0.00% | -1 to 10 (-1 denotes unrecorded/nonverbal) | Min -1, Median 5, Max 10 |
| `weight_kg` | `float64` | 0 | 0.00% | 30.0–250.0 kg | Min 35.0, Median 78.4, Max 210.5 |
| `height_cm` | `float64` | 0 | 0.00% | 120.0–220.0 cm | Min 135.0, Median 169.2, Max 205.0 |
| `bmi` | `float64` | 0 | 0.00% | 12.0–60.0 | Min 14.1, Median 27.2, Max 58.4 |
| `shock_index` | `float64` | 4,146 | 5.18% | HR / SBP (0.3–3.5) | Min 0.2, Median 0.73, Max 4.8 |
| `news2_score` | `int64` | 0 | 0.00% | 0–20 (National Early Warning Score) | Min 0, Median 2, Max 17 |
| `triage_acuity` | `int64` | 0 | 0.00% | 1–5 | **Target variable** |
| `disposition` | `object` (str) | 0 | 0.00% | Admitted, discharged, etc. | **Excluded (Post-arrival outcome)** |
| `ed_los_hours` | `float64` | 0 | 0.00% | Hours in ED | **Excluded (Post-arrival outcome)** |

### 2.4 Patient History Features (`patient_history.csv`)
26 columns covering 100,000 patients with binary (0/1) flags:
- Cardiovascular: `hx_hypertension` (44.2%), `hx_coronary_artery_disease` (18.1%), `hx_heart_failure` (9.4%), `hx_atrial_fibrillation` (8.1%), `hx_peripheral_vascular_disease` (5.2%)
- Metabolic: `hx_diabetes_type2` (22.3%), `hx_diabetes_type1` (3.1%), `hx_obesity` (28.4%), `hx_hypothyroidism` (7.2%), `hx_hyperthyroidism` (2.1%)
- Respiratory: `hx_copd` (12.3%), `hx_asthma` (15.4%)
- Renal & Hepatic: `hx_ckd` (7.8%), `hx_liver_disease` (4.6%)
- Neurological & Psychiatric: `hx_stroke_prior` (6.2%), `hx_dementia` (5.1%), `hx_epilepsy` (3.4%), `hx_depression` (19.2%), `hx_anxiety` (18.5%), `hx_substance_use_disorder` (8.3%)
- Oncologic & Immune: `hx_malignancy` (8.7%), `hx_immunosuppressed` (4.9%), `hx_hiv` (1.2%), `hx_coagulopathy` (3.8%)
- Obstetric: `hx_pregnant` (2.4%)

---

## 3. Dataset B: Hospital ER_Data Detailed Audit

### 3.1 Overview & Schema

| Field Name | Type | Unique Values | Missing Count | Missing % | Clinical Assessment |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Patient Id` | `object` | 9,216 | 0 | 0.00% | Direct synthetic identifier |
| `Patient Admission Date` | `object` | 9,176 | 0 | 0.00% | Timestamp (`DD-MM-YYYY HH:MM`) |
| `Patient First Inital` | `object` | 26 | 0 | 0.00% | PII initial |
| `Patient Last Name` | `object` | 8,400 | 0 | 0.00% | Direct PII surname |
| `Patient Gender` | `object` | 3 | 0 | 0.00% | `M`, `F`, `NC` |
| `Patient Age` | `int64` | 79 | 0 | 0.00% | Range 1 to 79 |
| `Patient Race` | `object` | 7 | 0 | 0.00% | Demographic ethnicity |
| `Department Referral` | `object` | 7 | 5,400 | 58.59% | General Practice, Orthopedics, Cardiology, etc. |
| `Patient Admission Flag` | `bool` | 2 | 0 | 0.00% | True: 4,612 (50.04%), False: 4,604 (49.96%) |
| `Patient Satisfaction Score`| `float64` | 11 | 6,699 | 72.69% | Post-discharge survey (1–10) |
| `Patient Waittime` | `int64` | 51 | 0 | 0.00% | Range 10–60 minutes, mean 35.26 min |
| `Patients CM` | `int64` | 2 | 0 | 0.00% | Binary clinical management indicator (0/1) |

### 3.2 Evaluation of Suitability for Clinical Priority Modeling
- **Conclusion**: `Hospital ER_Data.csv` **cannot** be used to train clinical priority models. It lacks presenting complaint, symptoms, vitals, medical history, and clinical urgency targets.
- **Appropriate Research Application**:
  1. Calibrating real-world outpatient arrival distributions and service times in the Phase 9 conference simulation.
  2. Benchmarking baseline queue wait times under unprioritized First-Come, First-Served conditions (empirical mean 35.26 min, std 14.74 min).
  3. Validating de-identification / privacy sanitation pipelines (stripping PII names and initial fields before research consumption).

---

## 4. Feature-to-Dataset Mapping Matrix

The following matrix maps the system's clinical requirements to actual columns in `triagegeist`:

| Required Clinical Feature | Actual Source Column(s) | Status | Missingness | Preprocessing Strategy | Role in System |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Patient Age** | `age` | Available | 0.0% | Numerical standard scaling | Model Input (Demographic) |
| **Sex** | `sex` | Available | 0.0% | One-hot encoding (`M`, `F`, `Other`) | Model Input (Demographic) |
| **Presenting System** | `chief_complaint_system` | Available | 0.0% | Categorical frequency/target encoding | Model Input (Current Visit) |
| **Raw Complaint Text** | `chief_complaint_raw` | Available | 0.0% | TF-IDF / NLP embedding | LLM / Text Feature |
| **Systolic BP** | `systolic_bp` | Available | 5.18% | Median imputation + missing indicator | Model Input (Vital Sign) |
| **Diastolic BP** | `diastolic_bp` | Available | 5.18% | Median imputation + missing indicator | Model Input (Vital Sign) |
| **Heart Rate** | `heart_rate` | Available | 0.0% | Robust scaling | Model Input (Vital Sign) |
| **Respiratory Rate** | `respiratory_rate` | Available | 3.83% | Median imputation + missing indicator | Model Input (Vital Sign) |
| **Temperature** | `temperature_c` | Available | 0.72% | Median imputation + missing indicator | Model Input (Vital Sign) |
| **Oxygen Saturation (SpO2)**| `spo2` | Available | 0.0% | Min-Max normalization | Model Input (Vital Sign) |
| **Glasgow Coma Scale** | `gcs_total` | Available | 0.0% | Integer (3–15) | Model Input (Vital Sign) |
| **Pain Score** | `pain_score` | Available | 0.0% | Treat -1 as separate indicator (`unrecorded`) | Model Input (Clinical Finding) |
| **Shock Index** | `shock_index` | Derivable (`HR/SBP`) | 5.18% | Computed derived ratio | Model Input (Physiological Index) |
| **Early Warning Score** | `news2_score` | Available | 0.0% | Integer score (0–20) | Model Input (Clinical Index) |
| **Comorbidity Count** | `num_comorbidities` | Available | 0.0% | Integer count | Model Input (History Summary) |
| **Active Medications** | `num_active_medications` | Available | 0.0% | Integer count | Model Input (History Summary) |
| **Prior ED Visits (12m)** | `num_prior_ed_visits_12m` | Available | 0.0% | Log1p transformation | Model Input (Utilization) |
| **Specific Comorbidities** | 25 `hx_*` columns in `patient_history.csv` | Available | 0.0% | Binary vector concatenation | Model Input (History-Aware Model B) |
| **Triage Acuity Target** | `triage_acuity` | Available | 0.0% | Multi-class label (1–5) | **Target Variable** |
| **Length of Stay** | `ed_los_hours` | Post-arrival | N/A | **STRICTLY EXCLUDED** (Data Leakage) | Evaluated outcome only |
| **Hospital Disposition** | `disposition` | Post-arrival | N/A | **STRICTLY EXCLUDED** (Data Leakage) | Evaluated outcome only |

---

## 5. Methodological Safeguards & Ethical Limitations

1. **Absence of Real OPD Acuity Labels**: Triagegeist originates from emergency department arrivals. True OPD triage involves sub-acute clinical nuances (e.g. chronic hypertension titration vs. hypertensive urgency). Models trained on ED triage must be presented as **decision-support suggestions** and require explicit clinician sign-off.
2. **Missing Data Not Equivalent to Normal**: In clinical practice, an unrecorded respiratory rate does not mean normal respiration—it often reflects triage haste or patient combativeness. Preprocessing must include explicit missingness indicator binary columns (`systolic_bp_missing = 1`) alongside imputed values.
3. **No Automatic Downgrading for New Patients**: A new patient registering with no historical records must be evaluated fairly on current presenting vitals and complaints, without artificial penalty for having 0 past visits.
