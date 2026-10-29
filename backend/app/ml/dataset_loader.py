"""Dataset Loader and Preprocessing for Triage ML Pipeline.

Implements strict clinical safety constraints:
1. Excludes post-arrival target leakage: 'disposition', 'ed_los_hours'.
2. Generates explicit missingness indicator features (missing vitals carry clinical signals).
3. Merges longitudinal patient history for Model B.
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

logger = logging.getLogger("medqueue.ml.loader")

# TARGET LEAKAGE BLACKLIST (Strictly forbidden from all feature sets)
TARGET_LEAKAGE_COLUMNS = [
    "disposition",        # Admitted vs Discharged (decided hours after arrival)
    "ed_los_hours",       # Length of stay in ED (future outcome)
]

# META & NON-CLINICAL COLUMNS (Not generalizable features)
META_COLUMNS = [
    "patient_id",
    "site_id",
    "triage_nurse_id",
    "arrival_month",
    "arrival_season",
    "shift",
    "arrival_day",
    "language",
    "insurance_type",
    "transport_origin",
    "pain_location",
    "weight_kg",
    "height_cm",
    "bmi",
]

# MODEL A (CURRENT ENCOUNTER ONLY) VITAL & OBSERVATION FEATURES
MODEL_A_NUMERICAL = [
    "age",
    "systolic_bp",
    "diastolic_bp",
    "mean_arterial_pressure",
    "pulse_pressure",
    "heart_rate",
    "respiratory_rate",
    "temperature_c",
    "spo2",
    "gcs_total",
    "pain_score",
    "shock_index",
    "news2_score",
]

# VITALS THAT RECEIVE EXPLICIT MISSINGNESS INDICATORS
VITAL_INDICATOR_COLS = [
    "systolic_bp",
    "diastolic_bp",
    "mean_arterial_pressure",
    "pulse_pressure",
    "heart_rate",
    "respiratory_rate",
    "temperature_c",
    "spo2",
    "shock_index",
    "pain_score",
    "gcs_total",
]

MODEL_A_CATEGORICAL = [
    "sex",
    "arrival_mode",
    "mental_status_triage",
    "chief_complaint_system",
]

# MODEL B ADDITIONAL FEATURES (LONGITUDINAL PATIENT HISTORY)
MODEL_B_HISTORY_NUMERICAL = [
    "num_prior_ed_visits_12m",
    "num_prior_admissions_12m",
    "num_active_medications",
    "num_comorbidities",
]

MODEL_B_COMORBIDITY_COLS = [
    "hx_hypertension",
    "hx_diabetes_type2",
    "hx_diabetes_type1",
    "hx_asthma",
    "hx_copd",
    "hx_heart_failure",
    "hx_atrial_fibrillation",
    "hx_ckd",
    "hx_liver_disease",
    "hx_malignancy",
    "hx_obesity",
    "hx_depression",
    "hx_anxiety",
    "hx_dementia",
    "hx_epilepsy",
    "hx_hypothyroidism",
    "hx_hyperthyroidism",
    "hx_hiv",
    "hx_coagulopathy",
    "hx_immunosuppressed",
    "hx_pregnant",
    "hx_substance_use_disorder",
    "hx_coronary_artery_disease",
    "hx_stroke_prior",
    "hx_peripheral_vascular_disease",
]


def resolve_data_paths() -> Tuple[Path, Path]:
    """Locate raw triagegeist dataset files.
    
    Directory layout (post-reorganization):
        backend/
            app/ml/dataset_loader.py  ← __file__
            data/raw/triagegeist/     ← datasets live here
    
    Path parents:
        parent   = backend/app/ml
        parent^2 = backend/app
        parent^3 = backend              ← backend_root
    """
    backend_root = Path(__file__).resolve().parent.parent.parent
    train_path = backend_root / "data" / "raw" / "triagegeist" / "train.csv"
    hist_path = backend_root / "data" / "raw" / "triagegeist" / "patient_history.csv"

    if not train_path.exists():
        # Legacy fallback: old layout where data/ was at project root
        project_root = backend_root.parent
        train_path = project_root / "data" / "raw" / "triagegeist" / "train.csv"
        hist_path = project_root / "data" / "raw" / "triagegeist" / "patient_history.csv"

    return train_path, hist_path


def load_raw_dataset(max_rows: Optional[int] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load train.csv and patient_history.csv with leakage auditing."""
    train_path, hist_path = resolve_data_paths()
    if not train_path.exists():
        raise FileNotFoundError(f"Triagegeist train.csv not found at {train_path}")

    logger.info(f"Loading raw dataset from {train_path} (max_rows={max_rows})...")
    train_df = pd.read_csv(train_path, nrows=max_rows)
    logger.info(f"Loaded train.csv: {train_df.shape[0]} rows, {train_df.shape[1]} columns")

    # Target leakage audit
    leakage_present = [c for c in TARGET_LEAKAGE_COLUMNS if c in train_df.columns]
    if leakage_present:
        logger.warning(
            f"DETECTED TARGET LEAKAGE COLUMNS in raw data: {leakage_present}. "
            "These will be strictly dropped from feature engineering."
        )

    hist_df = pd.DataFrame()
    if hist_path.exists():
        hist_df = pd.read_csv(hist_path)
        logger.info(f"Loaded patient_history.csv: {hist_df.shape[0]} records")
    else:
        logger.warning(f"patient_history.csv not found at {hist_path}")

    return train_df, hist_df


def engineer_features(
    df: pd.DataFrame,
    hist_df: Optional[pd.DataFrame] = None,
    include_history: bool = True,
) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
    """Build feature matrix with explicit missingness indicators and target leakage removal."""
    data = df.copy()

    # 1. Strictly drop leakage columns
    for leak_col in TARGET_LEAKAGE_COLUMNS:
        if leak_col in data.columns:
            data = data.drop(columns=[leak_col])

    # 2. Extract target if present
    target = None
    if "triage_acuity" in data.columns:
        target = data["triage_acuity"].astype(int)
        data = data.drop(columns=["triage_acuity"])

    # 3. Add explicit missingness indicators for vitals
    indicator_cols = []
    for col in VITAL_INDICATOR_COLS:
        if col in data.columns:
            ind_name = f"{col}_isna"
            data[ind_name] = data[col].isna().astype(float)
            indicator_cols.append(ind_name)

    # 4. Impute derived clinical scores if components exist but score is missing
    # MAP = DBP + (SBP - DBP)/3
    if "mean_arterial_pressure" in data.columns and "systolic_bp" in data.columns and "diastolic_bp" in data.columns:
        derived_map = data["diastolic_bp"] + (data["systolic_bp"] - data["diastolic_bp"]) / 3.0
        data["mean_arterial_pressure"] = data["mean_arterial_pressure"].fillna(derived_map)

    # Pulse Pressure = SBP - DBP
    if "pulse_pressure" in data.columns and "systolic_bp" in data.columns and "diastolic_bp" in data.columns:
        data["pulse_pressure"] = data["pulse_pressure"].fillna(data["systolic_bp"] - data["diastolic_bp"])

    # Shock Index = HR / SBP
    if "shock_index" in data.columns and "heart_rate" in data.columns and "systolic_bp" in data.columns:
        valid_sbp = data["systolic_bp"].replace(0, np.nan)
        data["shock_index"] = data["shock_index"].fillna(data["heart_rate"] / valid_sbp)

    # 5. Merge longitudinal medical history if requested (Model B)
    feature_columns = list(MODEL_A_NUMERICAL) + list(indicator_cols) + list(MODEL_A_CATEGORICAL)

    if include_history:
        if hist_df is not None and not hist_df.empty and "patient_id" in data.columns and "patient_id" in hist_df.columns:
            data = data.merge(hist_df, on="patient_id", how="left")
            for hx_col in MODEL_B_COMORBIDITY_COLS:
                if hx_col in data.columns:
                    data[hx_col] = data[hx_col].fillna(0).astype(float)
        else:
            # Add comorbidity columns as 0 if history dataframe not merged
            for hx_col in MODEL_B_COMORBIDITY_COLS:
                if hx_col not in data.columns:
                    data[hx_col] = 0.0

        for hist_num in MODEL_B_HISTORY_NUMERICAL:
            if hist_num not in data.columns:
                data[hist_num] = 0.0
            else:
                data[hist_num] = data[hist_num].fillna(0).astype(float)

        feature_columns += list(MODEL_B_HISTORY_NUMERICAL) + list(MODEL_B_COMORBIDITY_COLS)

    # Ensure all selected feature columns exist in the DataFrame
    selected_features = [col for col in feature_columns if col in data.columns]
    X = data[selected_features].copy()

    return X, target, selected_features


def prepare_train_val_split(
    max_rows: Optional[int] = 30000,
    val_size: float = 0.2,
    random_state: int = 42,
) -> Dict[str, any]:
    """Load dataset, build Model A and Model B feature sets, and split into train/validation sets."""
    train_df, hist_df = load_raw_dataset(max_rows=max_rows)

    # Build Model A (Current-only)
    X_a, y, feat_a = engineer_features(train_df, hist_df=None, include_history=False)

    # Build Model B (Current + Longitudinal History)
    X_b, _, feat_b = engineer_features(train_df, hist_df=hist_df, include_history=True)

    # Stratified Train/Val split ensuring identical train indices across Model A and B
    indices = np.arange(len(y))
    train_idx, val_idx = train_test_split(
        indices,
        test_size=val_size,
        stratify=y,
        random_state=random_state,
    )

    return {
        "X_train_a": X_a.iloc[train_idx],
        "X_val_a": X_a.iloc[val_idx],
        "X_train_b": X_b.iloc[train_idx],
        "X_val_b": X_b.iloc[val_idx],
        "y_train": y.iloc[train_idx],
        "y_val": y.iloc[val_idx],
        "features_a": feat_a,
        "features_b": feat_b,
        "train_size": len(train_idx),
        "val_size": len(val_idx),
    }
