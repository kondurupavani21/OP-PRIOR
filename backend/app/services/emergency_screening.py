"""Clinically Reviewed Emergency Warning-Sign Screening Engine.

Provides deterministic, rule-based screening for life-threatening physiological
instabilities and red-flag symptoms. Executes synchronously upon registration
to prevent clinical triage delays.

IMPORTANT CLINICAL NOTICE:
This screening pathway acts as an operational decision-support safety net.
It is NOT an autonomous diagnostic tool. Clinician assessment is mandatory.
"""
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class EmergencyScreeningResult(BaseModel):
    """Structured outcome of the emergency warning-sign pathway."""
    is_emergency: bool = Field(..., description="True if immediate emergency escalation criteria are met")
    escalation_level: str = Field(..., description="IMMEDIATE_ESCALATION, HIGH_PRIORITY, or STANDARD")
    escalation_reasons: List[str] = Field(default_factory=list, description="Clinical triggers identified")
    action_required: str = Field(..., description="Explicit clinical guidance for triage/reception staff")
    evaluated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


HIGH_RISK_SYMPTOM_INDICATORS = {
    "chest pain": "Potential Acute Coronary Syndrome / Myocardial Infarction",
    "difficulty breathing": "Severe Respiratory Distress",
    "shortness of breath": "Severe Respiratory Compromise",
    "unconscious": "Loss of Consciousness / Coma",
    "unresponsive": "Unresponsive State / GCS Depression",
    "stroke": "Suspected Cerebrovascular Accident / Acute Stroke Signs",
    "facial drooping": "Focal Neurological Deficit",
    "slurred speech": "Acute Neurological / Stroke Indicator",
    "anaphylaxis": "Acute Severe Allergic Reaction / Airway Threat",
    "severe bleeding": "Active Hemorrhage / Hypovolemia Risk",
    "seizure": "Active or Recent Generalized Seizure",
    "severe head injury": "Traumatic Brain Injury / Intracranial Pressure",
}


def run_emergency_screening(
    vitals: Optional[Dict[str, Any]] = None,
    symptoms: Optional[List[str]] = None,
    chief_complaint: Optional[str] = None,
    mental_status: Optional[str] = None,
) -> EmergencyScreeningResult:
    """Evaluate patient intake measurements against emergency clinical pathways."""
    vitals = vitals or {}
    symptoms = symptoms or []
    chief_complaint = (chief_complaint or "").lower()
    reasons: List[str] = []
    immediate_escalation = False

    # Extract vitals safely (avoiding silent normal defaults)
    spo2 = vitals.get("spo2")
    systolic_bp = vitals.get("systolic_bp")
    diastolic_bp = vitals.get("diastolic_bp")
    heart_rate = vitals.get("heart_rate")
    respiratory_rate = vitals.get("respiratory_rate")
    temperature_f = vitals.get("temperature")  # in Fahrenheit

    # 1. Oxygen Saturation (SpO2)
    if spo2 is not None:
        try:
            val_spo2 = float(spo2)
            if val_spo2 > 0 and val_spo2 < 90.0:
                if val_spo2 <= 70.0:
                    reasons.append(
                        f"CRITICAL HYPOXIA / SENSOR VERIFICATION: SpO2 {val_spo2}% (<90%) indicates life-threatening hypoxemia. "
                        "Immediate emergency assessment and acute oxygenation required. Staff must verify probe placement and "
                        "waveform to rule out measurement artifact without delaying supportive care."
                    )
                else:
                    reasons.append(f"CRITICAL HYPOXIA: SpO2 {val_spo2}% (<90%) indicates severe arterial desaturation.")
                immediate_escalation = True
            elif val_spo2 >= 90.0 and val_spo2 < 94.0:
                reasons.append(f"BORDERLINE OXYGENATION: SpO2 {val_spo2}% (<94%) requires close monitoring.")
        except (ValueError, TypeError):
            pass

    # 2. Blood Pressure (Hypertensive Crisis or Shock)
    try:
        if systolic_bp is not None:
            sbp = float(systolic_bp)
            if sbp >= 180.0:
                reasons.append(f"HYPERTENSIVE CRISIS: Systolic BP {sbp} mmHg (>=180 mmHg) risks acute end-organ damage.")
                immediate_escalation = True
            elif sbp < 90.0 and sbp > 0.0:
                reasons.append(f"HYPOTENSIVE SHOCK RISK: Systolic BP {sbp} mmHg (<90 mmHg) indicates hemodynamic collapse.")
                immediate_escalation = True

        if diastolic_bp is not None:
            dbp = float(diastolic_bp)
            if dbp >= 110.0:
                reasons.append(f"HYPERTENSIVE EMERGENCY: Diastolic BP {dbp} mmHg (>=110 mmHg).")
                immediate_escalation = True
    except (ValueError, TypeError):
        pass

    # 3. Heart Rate (Pulse bpm)
    if heart_rate is not None:
        try:
            hr = float(heart_rate)
            if hr > 130.0:
                reasons.append(f"SEVERE TACHYCARDIA: Heart rate {hr} bpm (>130 bpm).")
                immediate_escalation = True
            elif hr < 45.0 and hr > 0.0:
                reasons.append(f"CRITICAL BRADYCARDIA: Heart rate {hr} bpm (<45 bpm).")
                immediate_escalation = True
        except (ValueError, TypeError):
            pass

    # 4. Respiratory Rate
    if respiratory_rate is not None:
        try:
            rr = float(respiratory_rate)
            if rr > 32.0:
                reasons.append(f"SEVERE TACHYPNEA: Respiratory rate {rr}/min (>32/min) indicates respiratory failure.")
                immediate_escalation = True
            elif rr < 10.0 and rr > 0.0:
                reasons.append(f"RESPIRATORY DEPRESSION: Respiratory rate {rr}/min (<10/min) indicates hypoventilation.")
                immediate_escalation = True
        except (ValueError, TypeError):
            pass

    # 5. Core Temperature (Hyperpyrexia)
    if temperature_f is not None:
        try:
            temp = float(temperature_f)
            if temp >= 104.0:
                reasons.append(f"HYPERPYREXIA: Body temperature {temp}°F (>=104°F) carries neurological risk.")
        except (ValueError, TypeError):
            pass

    # 6. Mental Status
    if mental_status and mental_status.lower() in ["unresponsive", "confused", "lethargic", "stupor"]:
        reasons.append(f"ALTERED MENTAL STATUS: Patient reported as '{mental_status}'.")
        immediate_escalation = True

    # 7. Red-Flag Symptoms & Chief Complaint Screening
    combined_text = (chief_complaint + " " + " ".join([s.lower() for s in symptoms])).strip()
    for trigger, clinical_desc in HIGH_RISK_SYMPTOM_INDICATORS.items():
        if trigger in combined_text:
            reasons.append(f"RED-FLAG SYMPTOM: '{trigger.title()}' ({clinical_desc}).")
            immediate_escalation = True

    # Synthesize escalation status
    if immediate_escalation:
        return EmergencyScreeningResult(
            is_emergency=True,
            escalation_level="IMMEDIATE_ESCALATION",
            escalation_reasons=reasons,
            action_required=(
                "IMMEDIATE CLINICAL ESCALATION REQUIRED: Patient meets clinical red-flag criteria. "
                "Alert the on-duty emergency physician immediately and transfer to acute care bay. "
                "Do NOT retain in general outpatient queue. Clinical staff must recheck any potentially discordant vitals "
                "(including pulse oximeter probe placement) without delaying appropriate resuscitation. "
                "Emergency safety net warnings cannot be overridden by ML scoring or missing medical history; "
                "the clinician remains responsible for all final clinical decisions."
            ),
        )
    elif len(reasons) > 0:
        return EmergencyScreeningResult(
            is_emergency=False,
            escalation_level="HIGH_PRIORITY",
            escalation_reasons=reasons,
            action_required="EXPEDITED CLINICAL REVIEW: Monitor patient closely; prioritize for physician assessment.",
        )
    else:
        return EmergencyScreeningResult(
            is_emergency=False,
            escalation_level="STANDARD",
            escalation_reasons=[],
            action_required="Standard outpatient queue triage pathway.",
        )
