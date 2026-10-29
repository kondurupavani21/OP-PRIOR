"""Pydantic Schemas for Machine Learning Triage Prioritization."""
from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class TriagePredictionRequest(BaseModel):
    """Clinical feature payload for ML triage acuity inference."""
    age: float = Field(..., ge=0, le=125, description="Patient age in years")
    sex: str = Field(default="M", description="Biological sex (M, F, Other)")
    arrival_mode: str = Field(default="walk-in", description="Mode of arrival: walk-in, ambulance, public_transport")
    chief_complaint_system: str = Field(default="general", description="Clinical complaint category / system")
    mental_status_triage: str = Field(default="alert", description="Mental alertness: alert, drowsy, agitated, unresponsive")

    # Current Encounter Vitals (Explicitly nullable to handle missing measurements)
    systolic_bp: Optional[float] = Field(default=None, ge=30, le=300, description="Systolic Blood Pressure (mmHg)")
    diastolic_bp: Optional[float] = Field(default=None, ge=20, le=200, description="Diastolic Blood Pressure (mmHg)")
    heart_rate: Optional[float] = Field(default=None, ge=20, le=300, description="Heart rate (bpm)")
    respiratory_rate: Optional[float] = Field(default=None, ge=4, le=80, description="Respiratory rate (breaths/min)")
    temperature_c: Optional[float] = Field(default=None, ge=25.0, le=45.0, description="Core temperature in Celsius")
    spo2: Optional[float] = Field(default=None, ge=40.0, le=100.0, description="Pulse Oximetry Oxygen Saturation (%)")
    gcs_total: Optional[float] = Field(default=None, ge=3, le=15, description="Glasgow Coma Scale Total")
    pain_score: Optional[float] = Field(default=None, ge=0, le=10, description="Numeric Pain Scale (0-10)")

    # Longitudinal Medical History (Used by Model B)
    num_comorbidities: Optional[int] = Field(default=0, ge=0)
    num_active_medications: Optional[int] = Field(default=0, ge=0)
    num_prior_ed_visits_12m: Optional[int] = Field(default=0, ge=0)
    num_prior_admissions_12m: Optional[int] = Field(default=0, ge=0)
    comorbidities: Optional[List[str]] = Field(default_factory=list, description="Verified pre-existing chronic conditions")

    # Model Selection
    model_type: Optional[str] = Field(
        default="model_b_random_forest",
        description="Target model identifier: model_a_logistic_regression, model_a_random_forest, model_a_mlp, model_b_logistic_regression, model_b_random_forest, model_b_mlp"
    )


class AcuityProbability(BaseModel):
    """Probability score for a single triage acuity tier."""
    acuity_level: int = Field(..., ge=1, le=5, description="Acuity class 1-5 (1=Critical, 5=Non-urgent)")
    level_name: str = Field(..., description="Standard clinical urgency name")
    probability: float = Field(..., ge=0.0, le=1.0, description="Calibrated class probability")


class TriagePredictionResponse(BaseModel):
    """Result of ML triage acuity inference."""
    predicted_acuity: int = Field(..., ge=1, le=5)
    acuity_label: str
    urgency_tier: str = Field(..., description="HIGH (Acuity 1-2), MEDIUM (Acuity 3), LOW (Acuity 4-5)")
    confidence: float = Field(..., ge=0.0, le=1.0)
    probabilities: List[AcuityProbability]
    model_used: str
    is_emergency: bool
    missing_vitals_count: int
    missing_vitals: List[str]
    contributing_factors: List[str]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ModelStatusResponse(BaseModel):
    """Current state and metadata for ML inference engines."""
    is_trained: bool
    available_models: List[str]
    default_model: str
    trained_at: Optional[str] = None
    dataset_records: int = 0
    features_count: Dict[str, int] = Field(default_factory=dict)
    models_dir: str


class ModelEvaluationSummary(BaseModel):
    """Comparative performance metrics across models."""
    model_name: str
    model_family: str
    feature_set: str  # Model A (Current) vs Model B (History-Aware)
    macro_f1: float
    balanced_accuracy: float
    accuracy: float
    per_class_f1: Dict[str, float]
    confusion_matrix: List[List[int]]


class ModelEvaluationResponse(BaseModel):
    """Complete evaluation report for all trained models."""
    trained_at: str
    train_samples: int
    val_samples: int
    models: List[ModelEvaluationSummary]
    champion_model: str
    target_leakage_safeguards: List[str]
