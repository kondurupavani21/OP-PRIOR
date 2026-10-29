"""Machine Learning Training and Comparative Evaluation Pipeline for MedQueue AI.

Trains:
1. Model A (Current encounter vitals + missingness indicators + categoricals)
   - Logistic Regression (Baseline)
   - Random Forest Classifier
   - Multilayer Perceptron (MLP)
2. Model B (Current encounter + Longitudinal comorbidity history + prior ED visits)
   - Logistic Regression
   - Random Forest Classifier (Champion)
   - Multilayer Perceptron (MLP)

Enforces:
- Strict target leakage blacklist (NO 'disposition', NO 'ed_los_hours').
- Stratified validation splits.
- Macro F1 and Balanced Accuracy scoring (critical due to ~3.4% Acuity 1 class imbalance).
- Serializes trained pipelines to 'backend/models/' and generates 'backend/reports/model_evaluation_report.json'.
"""
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline

from app.ml.dataset_loader import (
    TARGET_LEAKAGE_COLUMNS,
    prepare_train_val_split,
)
from app.ml.preprocessor import build_preprocessor

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
logger = logging.getLogger("medqueue.ml.train")


def get_artifact_dirs() -> Tuple[Path, Path]:
    """Get paths for models directory and reports directory."""
    backend_root = Path(__file__).resolve().parent.parent.parent
    models_dir = backend_root / "models"
    reports_dir = backend_root / "reports"
    models_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    return models_dir, reports_dir


def train_and_evaluate_model(
    model_name: str,
    model_family: str,
    feature_set: str,
    pipeline: Pipeline,
    X_train,
    y_train,
    X_val,
    y_val,
    models_dir: Path,
) -> Dict[str, any]:
    """Train a pipeline, compute comprehensive metrics, and serialize."""
    logger.info(f"Training {model_name} ({feature_set})...")
    start_t = datetime.now()
    pipeline.fit(X_train, y_train)
    duration = (datetime.now() - start_t).total_seconds()
    logger.info(f"Fitted {model_name} in {duration:.1f}s. Evaluating on validation set...")

    y_pred = pipeline.predict(X_val)

    # Core comparative metrics
    macro_f1 = float(f1_score(y_val, y_pred, average="macro"))
    balanced_acc = float(balanced_accuracy_score(y_val, y_pred))
    acc = float(accuracy_score(y_val, y_pred))
    cm = confusion_matrix(y_val, y_pred, labels=[1, 2, 3, 4, 5]).tolist()

    report_dict = classification_report(
        y_val,
        y_pred,
        labels=[1, 2, 3, 4, 5],
        target_names=["Acuity 1 (Critical)", "Acuity 2 (Emergent)", "Acuity 3 (Urgent)", "Acuity 4 (Less Urgent)", "Acuity 5 (Non-Urgent)"],
        output_dict=True,
        zero_division=0,
    )

    per_class_f1 = {
        f"Acuity_{i}": float(report_dict[name]["f1-score"])
        for i, name in enumerate(
            ["Acuity 1 (Critical)", "Acuity 2 (Emergent)", "Acuity 3 (Urgent)", "Acuity 4 (Less Urgent)", "Acuity 5 (Non-Urgent)"],
            start=1,
        )
    }

    # Save model artifact
    model_file = models_dir / f"{model_name}.joblib"
    joblib.dump(pipeline, model_file)
    logger.info(f"Saved {model_name} to {model_file} (Macro F1: {macro_f1:.4f}, Balanced Acc: {balanced_acc:.4f})")

    return {
        "model_name": model_name,
        "model_family": model_family,
        "feature_set": feature_set,
        "training_duration_sec": round(duration, 2),
        "macro_f1": round(macro_f1, 4),
        "balanced_accuracy": round(balanced_acc, 4),
        "accuracy": round(acc, 4),
        "per_class_f1": per_class_f1,
        "confusion_matrix": cm,
        "artifact_file": str(model_file.name),
    }


def run_full_training_pipeline(max_rows: int = 35000) -> Dict[str, any]:
    """Execute complete dataset splitting, pipeline construction, training, and report generation."""
    models_dir, reports_dir = get_artifact_dirs()

    logger.info("=" * 70)
    logger.info(f"STARTING TRIAGE ML TRAINING PIPELINE (max_rows={max_rows})")
    logger.info("=" * 70)

    # 1. Prepare data splits
    splits = prepare_train_val_split(max_rows=max_rows, val_size=0.2, random_state=42)
    X_train_a = splits["X_train_a"]
    X_val_a = splits["X_val_a"]
    X_train_b = splits["X_train_b"]
    X_val_b = splits["X_val_b"]
    y_train = splits["y_train"]
    y_val = splits["y_val"]

    features_a = splits["features_a"]
    features_b = splits["features_b"]

    logger.info(f"Dataset split: Train={len(y_train)}, Val={len(y_val)}")
    logger.info(f"Model A features ({len(features_a)}): {features_a}")
    logger.info(f"Model B features ({len(features_b)}): {len(features_b)} total (includes longitudinal history & comorbidities)")

    # 2. Build preprocessors
    preprocessor_a = build_preprocessor(features_a)
    preprocessor_b = build_preprocessor(features_b)

    # Save preprocessor feature definitions
    meta_info = {
        "features_a": features_a,
        "features_b": features_b,
        "target_classes": [1, 2, 3, 4, 5],
        "class_labels": {
            1: "Critical / Immediate Resuscitation",
            2: "Emergent",
            3: "Urgent",
            4: "Less Urgent",
            5: "Non-Urgent",
        },
        "target_leakage_safeguards": TARGET_LEAKAGE_COLUMNS,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "train_samples": len(y_train),
        "val_samples": len(y_val),
    }
    with open(models_dir / "pipeline_metadata.json", "w") as f:
        json.dump(meta_info, f, indent=2)

    # 3. Model definitions
    model_configs = [
        # Model A - Current Only
        (
            "model_a_logistic_regression",
            "Logistic Regression",
            "Model A (Current Only)",
            Pipeline([
                ("prep", preprocessor_a),
                ("clf", LogisticRegression(max_iter=400, class_weight="balanced", random_state=42)),
            ]),
            X_train_a,
            X_val_a,
        ),
        (
            "model_a_random_forest",
            "Random Forest",
            "Model A (Current Only)",
            Pipeline([
                ("prep", preprocessor_a),
                ("clf", RandomForestClassifier(
                    n_estimators=100,
                    max_depth=12,
                    min_samples_split=8,
                    class_weight="balanced",
                    random_state=42,
                    n_jobs=-1,
                )),
            ]),
            X_train_a,
            X_val_a,
        ),
        (
            "model_a_mlp",
            "Multilayer Perceptron (MLP)",
            "Model A (Current Only)",
            Pipeline([
                ("prep", preprocessor_a),
                ("clf", MLPClassifier(
                    hidden_layer_sizes=(64, 32),
                    max_iter=60,
                    early_stopping=True,
                    random_state=42,
                )),
            ]),
            X_train_a,
            X_val_a,
        ),
        # Model B - Current + Longitudinal History
        (
            "model_b_logistic_regression",
            "Logistic Regression",
            "Model B (History-Aware)",
            Pipeline([
                ("prep", preprocessor_b),
                ("clf", LogisticRegression(max_iter=400, class_weight="balanced", random_state=42)),
            ]),
            X_train_b,
            X_val_b,
        ),
        (
            "model_b_random_forest",
            "Random Forest",
            "Model B (History-Aware)",
            Pipeline([
                ("prep", preprocessor_b),
                ("clf", RandomForestClassifier(
                    n_estimators=120,
                    max_depth=14,
                    min_samples_split=6,
                    class_weight="balanced",
                    random_state=42,
                    n_jobs=-1,
                )),
            ]),
            X_train_b,
            X_val_b,
        ),
        (
            "model_b_mlp",
            "Multilayer Perceptron (MLP)",
            "Model B (History-Aware)",
            Pipeline([
                ("prep", preprocessor_b),
                ("clf", MLPClassifier(
                    hidden_layer_sizes=(64, 32),
                    max_iter=60,
                    early_stopping=True,
                    random_state=42,
                )),
            ]),
            X_train_b,
            X_val_b,
        ),
    ]

    evaluation_results: List[Dict[str, any]] = []

    for name, family, feat_label, pipe, X_tr, X_va in model_configs:
        res = train_and_evaluate_model(
            model_name=name,
            model_family=family,
            feature_set=feat_label,
            pipeline=pipe,
            X_train=X_tr,
            y_train=y_train,
            X_val=X_va,
            y_val=y_val,
            models_dir=models_dir,
        )
        evaluation_results.append(res)

    # Determine Champion Model (highest Macro F1)
    sorted_models = sorted(evaluation_results, key=lambda x: x["macro_f1"], reverse=True)
    champion = sorted_models[0]["model_name"]
    logger.info(f"CHAMPION MODEL SELECTED: {champion} (Macro F1: {sorted_models[0]['macro_f1']})")

    # Save champion symlink/pointer
    champion_pipeline = joblib.load(models_dir / f"{champion}.joblib")
    joblib.dump(champion_pipeline, models_dir / "champion_model.joblib")

    # Complete evaluation summary report
    report = {
        "title": "MedQueue AI OPD Clinical Triage ML Evaluation Report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": "triagegeist",
        "train_samples": len(y_train),
        "val_samples": len(y_val),
        "champion_model": champion,
        "target_leakage_safeguards": TARGET_LEAKAGE_COLUMNS,
        "models": evaluation_results,
    }

    report_file = reports_dir / "model_evaluation_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Evaluation report written to {report_file}")
    logger.info("TRAINING AND EVALUATION COMPLETE.")
    return report


if __name__ == "__main__":
    run_full_training_pipeline()
