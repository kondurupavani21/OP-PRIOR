# Clinical & Operational Data Directory

This directory houses raw and processed data assets for the AI-assisted Outpatient Prioritization System.

## Directory Structure

```
data/
├── raw/
│   ├── triagegeist/               # Kaggle Triagegeist clinical triage dataset
│   │   ├── train.csv              # 80,000 ESI triage training records
│   │   ├── test.csv               # 20,000 hold-out test cases
│   │   ├── patient_history.csv    # 100,000 comorbidity burden flags
│   │   ├── chief_complaints.csv   # 100,000 complaint text & organ systems
│   │   └── sample_submission.csv
│   └── hospital_er/
│       └── Hospital_ER_Data.csv   # 9,216 operational ER visit & wait-time records
├── processed/                     # Preprocessed feature vectors and splits
└── README.md
```

## Data Provenance & Safety Notices

1. **Raw Data Isolation**: All raw CSV files in `data/raw/` are excluded from version control via `.gitignore`.
2. **Clinical Acuity Scope**: `triagegeist` provides ESI clinical acuity labels (1 to 5). It does not represent outpatient department cases directly; outpatient clinical triage treats sub-acute presentation differently.
3. **Target Leakage Prohibition**: `disposition` and `ed_los_hours` from `train.csv` represent post-arrival events and are blacklisted from feature engineering.
4. **Operational Wait Times**: `Hospital_ER_Data.csv` provides empirical wait times (mean 35.26 min) used solely to calibrate simulation baselines. It lacks clinical vitals and acuity labels.
