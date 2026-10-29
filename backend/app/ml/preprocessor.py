"""Scikit-Learn ColumnTransformer and Pipeline Preprocessor for Triage Features."""
from typing import List
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.ml.dataset_loader import (
    MODEL_A_NUMERICAL,
    MODEL_A_CATEGORICAL,
    MODEL_B_HISTORY_NUMERICAL,
    MODEL_B_COMORBIDITY_COLS,
    VITAL_INDICATOR_COLS,
)


def build_preprocessor(feature_columns: List[str]) -> ColumnTransformer:
    """Build a ColumnTransformer that handles numerical, indicator, and categorical features."""
    transformers = []

    # 1. Numerical continuous features
    num_cols = [c for c in feature_columns if c in MODEL_A_NUMERICAL or c in MODEL_B_HISTORY_NUMERICAL]
    if num_cols:
        num_pipe = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ])
        transformers.append(("num", num_pipe, num_cols))

    # 2. Binary missingness indicators
    indicator_cols = [c for c in feature_columns if c.endswith("_isna")]
    if indicator_cols:
        ind_pipe = Pipeline([
            ("imputer", SimpleImputer(strategy="constant", fill_value=0.0)),
        ])
        transformers.append(("ind", ind_pipe, indicator_cols))

    # 3. Binary comorbidity flags
    comorb_cols = [c for c in feature_columns if c in MODEL_B_COMORBIDITY_COLS]
    if comorb_cols:
        comorb_pipe = Pipeline([
            ("imputer", SimpleImputer(strategy="constant", fill_value=0.0)),
        ])
        transformers.append(("comorb", comorb_pipe, comorb_cols))

    # 4. Categorical features
    cat_cols = [c for c in feature_columns if c in MODEL_A_CATEGORICAL]
    if cat_cols:
        cat_pipe = Pipeline([
            ("imputer", SimpleImputer(strategy="constant", fill_value="unknown")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ])
        transformers.append(("cat", cat_pipe, cat_cols))

    return ColumnTransformer(transformers=transformers, remainder="drop")
