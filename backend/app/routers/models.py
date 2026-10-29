"""Machine Learning Triage Acuity API Router."""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.ml.inference import predictor_instance
from app.ml.train_pipeline import run_full_training_pipeline
from app.schemas.ml import (
    ModelEvaluationResponse,
    ModelStatusResponse,
    TriagePredictionRequest,
    TriagePredictionResponse,
)

logger = logging.getLogger("medqueue.routers.models")
router = APIRouter(prefix="/models", tags=["Machine Learning Triage Models"])


@router.get(
    "/status",
    response_model=ModelStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Triage ML Model Inventory and Training Status",
)
def get_models_status() -> ModelStatusResponse:
    """Check whether models are trained, list available model checkpoints, and show feature dimensions."""
    return predictor_instance.get_status()


@router.get(
    "/evaluation",
    response_model=Optional[ModelEvaluationResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Comparative Model Evaluation Report",
)
def get_model_evaluation() -> Optional[ModelEvaluationResponse]:
    """Retrieve Macro F1, Balanced Accuracy, and Confusion Matrices comparing Model A vs Model B across Logistic Regression, Random Forest, and MLP."""
    report = predictor_instance.get_evaluation_report()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model evaluation report not found. Please train models first.",
        )
    return report


@router.post(
    "/predict",
    response_model=TriagePredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Predict Clinical Acuity via ML Model",
)
def predict_triage_acuity(payload: TriagePredictionRequest) -> TriagePredictionResponse:
    """Execute real-time ML inference using Model A or Model B.

    Outputs 5-class calibrated probability distribution, predicted acuity (1-5),
    urgency tier, missingness signals, and contributing clinical factors.
    """
    try:
        return predictor_instance.predict(payload)
    except FileNotFoundError as fnf:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Model artifacts not available: {str(fnf)}. Please run training pipeline.",
        )
    except Exception as exc:
        logger.error(f"Prediction failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference execution failed: {str(exc)}",
        )


@router.post(
    "/train",
    status_code=status.HTTP_200_OK,
    summary="Trigger ML Pipeline Training",
)
def trigger_training(
    max_rows: int = Query(default=35000, ge=1000, le=100000, description="Number of training rows to load from Triagegeist dataset"),
):
    """Run full training of Model A and Model B across Logistic Regression, Random Forest, and MLP."""
    try:
        report = run_full_training_pipeline(max_rows=max_rows)
        return {
            "status": "success",
            "message": "Model training and evaluation successfully completed.",
            "champion_model": report.get("champion_model"),
            "train_samples": report.get("train_samples"),
            "val_samples": report.get("val_samples"),
        }
    except Exception as exc:
        logger.error(f"Training failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model training pipeline failed: {str(exc)}",
        )
