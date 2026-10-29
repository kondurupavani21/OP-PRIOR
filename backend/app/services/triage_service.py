"""MedQueue AI Triage & Priority Scoring Service.

Implements transparent, explainable triage algorithms based on vital signs,
presenting symptoms, comorbidities, and demographic risk factors.
"""
from typing import List
from app.schemas.triage import TriageInput, TriageResult, PriorityFactor

CRITICAL_SYMPTOMS = {
    "chest pain",
    "shortness of breath",
    "difficulty breathing",
    "severe bleeding",
    "unconscious",
    "fainting",
    "stroke signs",
    "seizure",
    "severe head injury",
    "severe allergic reaction",
    "anaphylaxis",
}

MODERATE_SYMPTOMS = {
    "high fever",
    "persistent vomiting",
    "fracture",
    "acute abdominal pain",
    "asthma flare",
    "burn",
    "deep cut",
    "severe headache",
}


def calculate_triage_priority(data: TriageInput) -> TriageResult:
    """Calculate urgency score (0-100), severity level, and contributing factors."""
    score = 20  # Base score for outpatient check-in
    factors: List[PriorityFactor] = []

    # 1. Oxygen Saturation (SpO2)
    spo2 = data.spo2
    if spo2 is None:
        factors.append(PriorityFactor(
            title="SpO2 Unrecorded",
            description="Oxygen saturation not recorded at triage; requires clinical measurement",
            points="+0",
            level="info",
        ))
    elif spo2 > 0:
        if spo2 < 90:
            pts = 60 if spo2 <= 70 else 40
            score += pts
            desc = (
                f"Oxygen saturation dangerously low at {spo2}%. Immediate emergency assessment required; "
                "recheck probe placement and waveform to exclude measurement error without delaying supportive care."
                if spo2 <= 70
                else f"Oxygen saturation critically low at {spo2}%"
            )
            factors.append(PriorityFactor(
                title="Profound Critical Hypoxia" if spo2 <= 70 else "Critical Hypoxia",
                description=desc,
                points=f"+{pts}",
                level="critical",
            ))
        elif spo2 <= 94:
            score += 18
            factors.append(PriorityFactor(
                title="Mild-Moderate Hypoxia",
                description=f"Oxygen saturation is sub-optimal at {spo2}%",
                points="+18",
                level="warning",
            ))

    # 2. Heart Rate (bpm)
    hr = data.heart_rate or 75
    if hr > 0:
        if hr > 125 or hr < 45:
            score += 24
            factors.append(PriorityFactor(
                title="Severe Dysrhythmia / Tachycardia",
                description=f"Critical pulse rate ({hr} bpm)",
                points="+24",
                level="critical",
            ))
        elif hr > 100 or hr < 55:
            score += 12
            factors.append(PriorityFactor(
                title="Elevated Pulse Rate",
                description=f"Resting pulse rate is out of normal band ({hr} bpm)",
                points="+12",
                level="warning",
            ))

    # 3. Blood Pressure
    bp_str = str(data.blood_pressure or "120/80").strip()
    systolic = 120
    diastolic = 80
    if "/" in bp_str:
        try:
            parts = bp_str.split("/")
            systolic = int(parts[0].strip())
            diastolic = int(parts[1].strip())
        except (ValueError, IndexError):
            systolic, diastolic = 120, 80

    if systolic >= 180 or diastolic >= 110:
        score += 26
        factors.append(PriorityFactor(
            title="Hypertensive Crisis Range",
            description=f"Blood pressure measured at {systolic}/{diastolic} mmHg",
            points="+26",
            level="critical",
        ))
    elif systolic >= 150 or diastolic >= 95:
        score += 16
        factors.append(PriorityFactor(
            title="Stage 2 Hypertension",
            description=f"Significantly elevated blood pressure ({systolic}/{diastolic} mmHg)",
            points="+16",
            level="warning",
        ))
    elif systolic < 90 and systolic > 0:
        score += 22
        factors.append(PriorityFactor(
            title="Hypotension / Shock Risk",
            description=f"Systolic blood pressure low ({systolic} mmHg)",
            points="+22",
            level="critical",
        ))

    # 4. Body Temperature (°F)
    temp = data.temperature or 98.6
    if temp > 0:
        if temp >= 103.0:
            score += 20
            factors.append(PriorityFactor(
                title="Hyperpyrexia (Critical High Fever)",
                description=f"High fever measured at {temp:.1f}°F",
                points="+20",
                level="critical",
            ))
        elif temp >= 100.4:
            score += 10
            factors.append(PriorityFactor(
                title="Pyrexia / Elevated Temperature",
                description=f"Mild-to-moderate fever ({temp:.1f}°F)",
                points="+10",
                level="warning",
            ))
        elif temp < 95.0:
            score += 18
            factors.append(PriorityFactor(
                title="Hypothermia Alert",
                description=f"Core body temperature low ({temp:.1f}°F)",
                points="+18",
                level="critical",
            ))

    # 5. Blood Glucose (mg/dL)
    sugar = data.sugar_level or 100.0
    if sugar > 0:
        if sugar >= 300 or sugar <= 60:
            score += 22
            factors.append(PriorityFactor(
                title="Critical Glycemic Variance",
                description=f"Blood glucose level at {sugar:.0f} mg/dL (DKA or Hypoglycemia risk)",
                points="+22",
                level="critical",
            ))
        elif sugar >= 200:
            score += 10
            factors.append(PriorityFactor(
                title="Hyperglycemia",
                description=f"Elevated blood glucose ({sugar:.0f} mg/dL)",
                points="+10",
                level="warning",
            ))

    # 6. Age Acuity
    age = data.age
    if age <= 2 or age >= 70:
        score += 15
        factors.append(PriorityFactor(
            title="High-Risk Age Group",
            description=f"Patient age ({age} yrs) requires elevated clinical monitoring",
            points="+15",
            level="warning",
        ))
    elif age <= 5 or age >= 60:
        score += 8
        factors.append(PriorityFactor(
            title="Vulnerable Age Demographic",
            description=f"Patient age ({age} yrs)",
            points="+8",
            level="warning",
        ))

    # 7. Symptoms Analysis
    symptoms_list = [s.strip().lower() for s in (data.symptoms or []) if s.strip()]
    for s in symptoms_list:
        if any(crit in s for crit in CRITICAL_SYMPTOMS):
            score += 28
            factors.append(PriorityFactor(
                title=f"Critical Symptom: {s.title()}",
                description="Red flag symptom demanding urgent triage prioritization",
                points="+28",
                level="critical",
            ))
        elif any(mod in s for mod in MODERATE_SYMPTOMS):
            score += 14
            factors.append(PriorityFactor(
                title=f"Moderate Symptom: {s.title()}",
                description="Significant discomfort or clinical impairment",
                points="+14",
                level="warning",
            ))

    # 8. Comorbidities
    diseases = [d.strip() for d in (data.previous_diseases or []) if d.strip()]
    if diseases:
        points = min(len(diseases) * 6, 18)
        score += points
        factors.append(PriorityFactor(
            title="Underlying Chronic Illness",
            description=f"Pre-existing condition(s): {', '.join(diseases)}",
            points=f"+{points}",
            level="warning",
        ))

    # Clamp priority score between 0 and 100
    priority_score = max(0, min(100, score))

    # Independent Emergency Screening Safety Layer:
    # Any critical hypoxia (SpO2 < 90%, including 60%) must NEVER be LOW or non-emergency.
    has_critical_hypoxia = (data.spo2 is not None and 0 < data.spo2 < 90)
    if has_critical_hypoxia:
        priority_score = max(priority_score, 90)

    # Determine Severity Category & Target Wait
    if priority_score >= 75 or has_critical_hypoxia:
        severity = "HIGH"
        is_emergency = True
        recommended_wait_mins = 5
        summary = (
            "EMERGENCY / HIGH PRIORITY (Red Tier) - Immediate physician evaluation recommended. "
            "Staff must verify probe placement if severe hypoxia is detected without delaying supportive care."
            if has_critical_hypoxia
            else "HIGH PRIORITY (Red Tier) - Immediate physician evaluation recommended."
        )
    elif priority_score >= 45:
        severity = "MEDIUM"
        is_emergency = False
        recommended_wait_mins = 20
        summary = "MEDIUM PRIORITY (Yellow Tier) - Urgent outpatient examination needed."
    else:
        severity = "LOW"
        is_emergency = False
        recommended_wait_mins = 45
        summary = "LOW PRIORITY (Green Tier) - Routine consultation queue."

    return TriageResult(
        priority_score=priority_score,
        severity=severity,
        is_emergency=is_emergency,
        recommended_wait_mins=recommended_wait_mins,
        factors=factors,
        summary=summary,
    )
