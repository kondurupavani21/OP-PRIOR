# MedQueue AI - Clinical Triage Model Card

## 1. Model Overview
- **Model Name**: MedQueue Triage Acuity Predictor (Model A Current-Only vs Model B History-Aware)
- **Champion Architecture**: Multi-Class Balanced Random Forest (`model_b_random_forest`)
- **Alternative Baselines**: Multinomial Logistic Regression (`class_weight='balanced'`), Multilayer Perceptron (`MLPClassifier`)
- **Target**: Emergency Severity Acuity Level 1 to 5:
  - **Acuity 1**: Immediate Resuscitation / Critical (Life-threatening collapse, severe hypoxia, cardiac arrest)
  - **Acuity 2**: Emergent (Severe pain, altered mental status, severe dysrhythmia)
  - **Acuity 3**: Urgent (Multiple systemic symptoms, requires multi-resource evaluation)
  - **Acuity 4**: Less Urgent (Single uncomplicated complaint)
  - **Acuity 5**: Non-Urgent (Routine medication renewal, minor wound review)

---

## 2. Target Leakage Prevention & Data Hygiene
In compliance with strict clinical informatics guidelines, all post-arrival outcomes were audited and blacklisted:
- **`disposition`** (Admitted vs Discharged): Strictly excluded. (Decided hours after triage assessment).
- **`ed_los_hours`** (Total emergency length of stay): Strictly excluded. (Total stay duration is an outcome, not an input).
- **Identifiers & Non-generalizable Features**: `patient_id`, `site_id`, `triage_nurse_id`, `shift`, `arrival_day`, `arrival_month` were removed to prevent site-specific overfitting.

---

## 3. Explicit Missingness Indicator Modeling
In outpatient and emergency triage, missing vitals are not missing at random (`MNAR`). Patients who are collapsed or combative cannot provide complete blood pressure or height measurements; conversely, low-acuity walk-ins may only receive partial screenings.
Rather than silently replacing missing values with normal population averages, each vital sign has an explicit missingness indicator feature:
- `systolic_bp_isna`
- `diastolic_bp_isna`
- `heart_rate_isna`
- `respiratory_rate_isna`
- `temperature_c_isna`
- `spo2_isna`
- `shock_index_isna`
- `mean_arterial_pressure_isna`

This enables tree-based and linear models to preserve the clinical urgency signal inherent to unobtained vital signs.

---

## 4. Empirical Evaluation Results

Evaluated on 7,000 stratified validation cases (trained on 28,000 cases):

| Model Architecture | Feature Set | Macro F1 | Balanced Accuracy | Accuracy | Training Time |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Random Forest (Champion)** | **Model B (History-Aware)** | **0.8550** | **0.8663** | **0.8571** | **1.9s** |
| Multilayer Perceptron (MLP) | Model B (History-Aware) | 0.8477 | 0.8439 | 0.8492 | 3.8s |
| Random Forest | Model A (Current-Only) | 0.8394 | 0.8598 | 0.8415 | 1.6s |
| Multilayer Perceptron (MLP) | Model A (Current-Only) | 0.8383 | 0.8401 | 0.8390 | 7.5s |
| Logistic Regression | Model B (History-Aware) | 0.8279 | 0.8463 | 0.8290 | 6.6s |
| Logistic Regression (Baseline) | Model A (Current-Only) | 0.8102 | 0.8313 | 0.8120 | 6.0s |

### Key Research Findings:
1. **Longitudinal History Value**: Across all three algorithm families, incorporating verified comorbidity history (`Model B`) provided a consistent +1.0% to +1.8% lift in Macro F1 over current-encounter vitals alone (`Model A`).
2. **Class Imbalance Resilience**: Despite Acuity 1 representing only ~3.4% of total presentations, balanced class weighting and missingness indicators enabled the champion model to achieve a per-class F1 of >0.83 on critical resuscitation cases without drowning in Acuity 3 majority cases.

---

## 5. Clinical Safety & Intended Use
- **Decision-Support Only**: Model predictions are assistive recommendations for the triage nurse and consulting physician. The system displays predicted acuity alongside transparent contributing factors and calibrated probability bars.
- **Synchronous Override Safeguard**: A deterministic emergency screening rule engine executes synchronously before and alongside ML inference. If physiological vitals breach critical red-line thresholds (e.g., SpO2 < 90% or SBP < 90 mmHg), immediate clinical escalation is triggered regardless of model confidence.
- **Append-Only Auditing**: Any doctor modification or override of the ML-recommended triage tier requires mandatory clinical justification and is logged immutably in the `doctor_overrides` collection.
