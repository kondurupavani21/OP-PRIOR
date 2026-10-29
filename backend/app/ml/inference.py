"""ML Inference Engine for Clinical Triage Acuity Assessment."""
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
import joblib
import numpy as np
import pandas as pd

from app.schemas.ml import (
    AcuityProbability,
    ModelEvaluationResponse,
    ModelEvaluationSummary,
    ModelStatusResponse,
    TriagePredictionRequest,
    TriagePredictionResponse,
)
from app.services.emergency_screening import run_emergency_screening

logger = logging.getLogger("medqueue.ml.inference")

ACUITY_LABELS = {
    1: "Acuity 1: Critical / Immediate Resuscitation",
    2: "Acuity 2: Emergent",
    3: "Acuity 3: Urgent",
    4: "Acuity 4: Less Urgent",
    5: "Acuity 5: Non-Urgent",
}

ACUITY_TIERS = {
    1: "HIGH",
    2: "HIGH",
    3: "MEDIUM",
    4: "LOW",
    5: "LOW",
}


class TriageMLPredictor:
    """Inference service maintaining cached trained models and metadata."""

    def __init__(self):
        backend_root = Path(__file__).resolve().parent.parent.parent
        self.models_dir = backend_root / "models"
        self.reports_dir = backend_root / "reports"
        self._loaded_models: Dict[str, any] = {}
        self._metadata: Optional[Dict[str, any]] = None

    def get_metadata(self) -> Dict[str, any]:
        """Load or return cached pipeline metadata."""
        if self._metadata is None:
            meta_file = self.models_dir / "pipeline_metadata.json"
            if meta_file.exists():
                with open(meta_file, "r") as f:
                    self._metadata = json.load(f)
            else:
                self._metadata = {}
        return self._metadata

    def list_available_models(self) -> List[str]:
        """Return list of serialized joblib model files available."""
        if not self.models_dir.exists():
            return []
        files = list(self.models_dir.glob("*.joblib"))
        return [f.stem for f in sorted(files) if f.stem != "champion_model"]

    def load_model(self, model_identifier: str = "model_b_random_forest"):
        """Load pipeline from cache or disk."""
        # Normalize name
        clean_name = model_identifier.replace(".joblib", "")
        if clean_name in self._loaded_models:
            return self._loaded_models[clean_name]

        model_path = self.models_dir / f"{clean_name}.joblib"
        if not model_path.exists():
            # Try champion fallback
            champ_path = self.models_dir / "champion_model.joblib"
            if champ_path.exists():
                logger.warning(f"Model '{clean_name}' not found. Falling back to champion_model.")
                model_path = champ_path
                clean_name = "champion_model"
            else:
                raise FileNotFoundError(f"Trained model '{clean_name}' not found at {model_path}")

        logger.info(f"Loading ML pipeline: {model_path}")
        pipeline = joblib.load(model_path)
        self._loaded_models[clean_name] = pipeline
        return pipeline

    def get_status(self) -> ModelStatusResponse:
        """Get model inventory and training status."""
        available = self.list_available_models()
        meta = self.get_metadata()
        is_trained = len(available) > 0 and (self.models_dir / "champion_model.joblib").exists()

        return ModelStatusResponse(
            is_trained=is_trained,
            available_models=available,
            default_model="model_b_random_forest" if "model_b_random_forest" in available else (available[0] if available else "none"),
            trained_at=meta.get("trained_at"),
            dataset_records=meta.get("train_samples", 0) + meta.get("val_samples", 0),
            features_count={
                "model_a_features": len(meta.get("features_a", [])),
                "model_b_features": len(meta.get("features_b", [])),
            },
            models_dir=str(self.models_dir),
        )

    def get_evaluation_report(self) -> Optional[ModelEvaluationResponse]:
        """Load and return evaluation report."""
        report_file = self.reports_dir / "model_evaluation_report.json"
        if not report_file.exists():
            return None

        with open(report_file, "r") as f:
            data = json.load(f)

        models_list = [
            ModelEvaluationSummary(
                model_name=m["model_name"],
                model_family=m["model_family"],
                feature_set=m["feature_set"],
                macro_f1=m["macro_f1"],
                balanced_accuracy=m["balanced_accuracy"],
                accuracy=m["accuracy"],
                per_class_f1=m["per_class_f1"],
                confusion_matrix=m["confusion_matrix"],
            )
            for m in data.get("models", [])
        ]

        return ModelEvaluationResponse(
            trained_at=data.get("generated_at", ""),
            train_samples=data.get("train_samples", 0),
            val_samples=data.get("val_samples", 0),
            models=models_list,
            champion_model=data.get("champion_model", "model_b_random_forest"),
            target_leakage_safeguards=data.get("target_leakage_safeguards", []),
        )

    def predict(self, req: TriagePredictionRequest) -> TriagePredictionResponse:
        """Run ML inference for a patient clinical payload."""
        selected_model_name = req.model_type or "model_b_random_forest"
        pipeline = self.load_model(selected_model_name)
        meta = self.get_metadata()

        is_model_b = "model_b" in selected_model_name.lower() or selected_model_name == "champion_model"
        expected_features = meta.get("features_b" if is_model_b else "features_a", [])

        # 0. Independent Emergency Screening Layer (Pre-ML Safety Net)
        temp_f = (req.temperature_c * 9.0 / 5.0 + 32.0) if req.temperature_c is not None else None
        emergency_eval = run_emergency_screening(
            vitals={
                "spo2": req.spo2,
                "systolic_bp": req.systolic_bp,
                "diastolic_bp": req.diastolic_bp,
                "heart_rate": req.heart_rate,
                "respiratory_rate": req.respiratory_rate,
                "temperature": temp_f,
            },
            symptoms=[],
            chief_complaint=req.chief_complaint_system,
            mental_status=req.mental_status_triage,
        )

        # 1. Identify missing vitals
        missing_vitals: List[str] = []
        vital_checks = [
            ("systolic_bp", req.systolic_bp),
            ("diastolic_bp", req.diastolic_bp),
            ("heart_rate", req.heart_rate),
            ("respiratory_rate", req.respiratory_rate),
            ("temperature_c", req.temperature_c),
            ("spo2", req.spo2),
            ("gcs_total", req.gcs_total),
            ("pain_score", req.pain_score),
        ]
        for name, val in vital_checks:
            if val is None:
                missing_vitals.append(name)

        # 2. Derive physiological indices if missing
        sbp = req.systolic_bp
        dbp = req.diastolic_bp
        hr = req.heart_rate

        map_val = None
        pulse_press = None
        shock_idx = None

        if sbp is not None and dbp is not None:
            map_val = dbp + (sbp - dbp) / 3.0
            pulse_press = sbp - dbp

        if hr is not None and sbp is not None and sbp > 0:
            shock_idx = hr / sbp

        # NEWS2 approximation based on available components
        news2 = 0
        if req.spo2 is not None:
            if req.spo2 <= 91:
                news2 += 3
            elif req.spo2 <= 93:
                news2 += 2
            elif req.spo2 <= 95:
                news2 += 1
        if req.respiratory_rate is not None:
            if req.respiratory_rate <= 8 or req.respiratory_rate >= 25:
                news2 += 3
            elif req.respiratory_rate >= 21:
                news2 += 2
            elif req.respiratory_rate <= 11:
                news2 += 1
        if hr is not None:
            if hr <= 40 or hr >= 131:
                news2 += 3
            elif hr >= 111:
                news2 += 2
            elif hr <= 50 or hr >= 91:
                news2 += 1
        if sbp is not None:
            if sbp <= 90:
                news2 += 3
            elif sbp <= 100:
                news2 += 2
            elif sbp <= 110:
                news2 += 1

        # 3. Build single-row feature dictionary
        row_dict: Dict[str, any] = {
            "age": req.age,
            "sex": req.sex or "M",
            "arrival_mode": req.arrival_mode or "walk-in",
            "mental_status_triage": req.mental_status_triage or "alert",
            "chief_complaint_system": req.chief_complaint_system or "general",
            "systolic_bp": sbp,
            "diastolic_bp": dbp,
            "mean_arterial_pressure": map_val,
            "pulse_pressure": pulse_press,
            "heart_rate": hr,
            "respiratory_rate": req.respiratory_rate,
            "temperature_c": req.temperature_c,
            "spo2": req.spo2,
            "gcs_total": req.gcs_total if req.gcs_total is not None else 15.0,
            "pain_score": req.pain_score if req.pain_score is not None else 0.0,
            "shock_index": shock_idx,
            "news2_score": news2,
        }

        # Explicit missingness indicator features
        for vname, _ in vital_checks:
            row_dict[f"{vname}_isna"] = 1.0 if vname in missing_vitals else 0.0
        row_dict["shock_index_isna"] = 1.0 if shock_idx is None else 0.0
        row_dict["mean_arterial_pressure_isna"] = 1.0 if map_val is None else 0.0
        row_dict["pulse_pressure_isna"] = 1.0 if pulse_press is None else 0.0

        # Medical History features for Model B
        if is_model_b:
            row_dict["num_comorbidities"] = float(req.num_comorbidities or 0)
            row_dict["num_active_medications"] = float(req.num_active_medications or 0)
            row_dict["num_prior_ed_visits_12m"] = float(req.num_prior_ed_visits_12m or 0)
            row_dict["num_prior_admissions_12m"] = float(req.num_prior_admissions_12m or 0)

            # Map specific verified comorbidities
            verified_comorbs = [c.lower().strip() for c in (req.comorbidities or [])]
            comorb_keys = [
                "hx_hypertension", "hx_diabetes_type2", "hx_diabetes_type1", "hx_asthma",
                "hx_copd", "hx_heart_failure", "hx_atrial_fibrillation", "hx_ckd",
                "hx_liver_disease", "hx_malignancy", "hx_obesity", "hx_depression",
                "hx_anxiety", "hx_dementia", "hx_epilepsy", "hx_hypothyroidism",
                "hx_hyperthyroidism", "hx_hiv", "hx_coagulopathy", "hx_immunosuppressed",
                "hx_pregnant", "hx_substance_use_disorder", "hx_coronary_artery_disease",
                "hx_stroke_prior", "hx_peripheral_vascular_disease",
            ]
            for ck in comorb_keys:
                clean_term = ck.replace("hx_", "").replace("_", " ")
                row_dict[ck] = 1.0 if any(clean_term in vc or vc in clean_term for vc in verified_comorbs) else 0.0

        # Create DataFrame
        feature_df = pd.DataFrame([row_dict])

        # If expected features are known from metadata, ensure all exist
        if expected_features:
            for col in expected_features:
                if col not in feature_df.columns:
                    feature_df[col] = np.nan if not col.endswith("_isna") else 0.0
            feature_df = feature_df[expected_features]

        # 4. Execute prediction
        predicted_class = int(pipeline.predict(feature_df)[0])
        probabilities_raw = pipeline.predict_proba(feature_df)[0]

        # Map classes to standard 1..5
        classes_in_model = list(pipeline.classes_)
        prob_map: Dict[int, float] = {cls_id: 0.0 for cls_id in range(1, 6)}
        for idx, cls_id in enumerate(classes_in_model):
            prob_map[int(cls_id)] = float(probabilities_raw[idx])

        probabilities_list = [
            AcuityProbability(
                acuity_level=level,
                level_name=ACUITY_LABELS[level],
                probability=round(prob_map[level], 4),
            )
            for level in range(1, 6)
        ]

        confidence = round(prob_map.get(predicted_class, max(prob_map.values())), 4)

        # Independent Emergency Screening Safety Layer (runs before final dispatch)
        # Clinical emergency safety net cannot be overridden by normal ML predictions or missing medical history.
        # An SpO2 reading of 60% (or any SpO2 < 90%) must never be categorized as LOW priority.
        if emergency_eval.is_emergency:
            is_emergency = True
            urgency_tier = "HIGH"
            predicted_class = min(predicted_class, 1)
        else:
            urgency_tier = ACUITY_TIERS.get(predicted_class, "MEDIUM")
            is_emergency = predicted_class <= 2

        # 5. Extract contributing clinical factors
        factors: List[str] = []
        if emergency_eval.is_emergency:
            for reason in emergency_eval.escalation_reasons:
                factors.append(f"EMERGENCY SAFETY OVERRIDE: {reason}")
            factors.append(
                "CLINICAL GOVERNANCE: Emergency safety warning cannot be overridden by ML scoring or missing medical history. "
                "The qualified clinician remains responsible for all final clinical and triage decisions."
            )
        if req.spo2 is not None and req.spo2 < 92:
            factors.append(f"Hypoxia detected: SpO2 {req.spo2:.1f}%")
        if sbp is not None and (sbp >= 180 or (dbp is not None and dbp >= 110)):
            factors.append(f"Severe Hypertensive range: {sbp:.0f}/{dbp or 0:.0f} mmHg")
        if sbp is not None and sbp < 90:
            factors.append(f"Hypotension/Shock risk: SBP {sbp:.0f} mmHg")
        if hr is not None and (hr > 125 or hr < 45):
            factors.append(f"Marked Dysrhythmia/Tachycardia: {hr:.0f} bpm")
        if req.respiratory_rate is not None and (req.respiratory_rate > 30 or req.respiratory_rate < 10):
            factors.append(f"Critical Respiratory Variance: {req.respiratory_rate:.0f} bpm")
        if req.mental_status_triage in ["drowsy", "agitated", "unresponsive"]:
            factors.append(f"Altered Mental Status: '{req.mental_status_triage}'")
        if req.age >= 75 or req.age <= 2:
            factors.append(f"Vulnerable Age Group: {req.age:.0f} yrs")
        if is_model_b and (req.num_comorbidities or 0) >= 3:
            factors.append(f"Multiple Multimorbid Chronic Conditions ({req.num_comorbidities})")
        if missing_vitals:
            factors.append(f"Unobtainable/Missing Vitals at Intake: {', '.join(missing_vitals)}")

        if not factors:
            factors.append("Vital signs and triage markers within standard outpatient tolerances")

        return TriagePredictionResponse(
            predicted_acuity=predicted_class,
            acuity_label=ACUITY_LABELS.get(predicted_class, f"Acuity {predicted_class}"),
            urgency_tier=urgency_tier,
            confidence=confidence,
            probabilities=probabilities_list,
            model_used=selected_model_name,
            is_emergency=is_emergency,
            missing_vitals_count=len(missing_vitals),
            missing_vitals=missing_vitals,
            contributing_factors=factors,
            created_at=datetime.now(timezone.utc),
        )


# Global singleton instance
predictor_instance = TriageMLPredictor()
