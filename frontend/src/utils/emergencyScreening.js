/**
 * emergencyScreening.js
 * Frontend Real-Time Emergency Warning Screening Engine.
 *
 * Synchronously alerts clinical and intake staff of critical physiological thresholds
 * (hypoxia, hypertensive crisis, hypotensive shock, extreme pulse, and acute red-flag symptoms)
 * before and during encounter registration.
 *
 * ARCHITECTURE NOTE:
 * This function mirrors the backend emergency_screening.py logic.
 * `isEmergency = true` (immediate escalation) is set ONLY when there is an objective
 * physiological abnormality detected in the vitals, or when an altered mental status is recorded.
 * Red-flag symptoms alone (e.g. patient-reported "shortness of breath") raise a HIGH_PRIORITY
 * warning but do NOT set isEmergency=true, because symptom self-report without abnormal vitals
 * is insufficient to trigger the emergency escalation pathway. This mirrors the backend rule.
 *
 * DISCLAIMER:
 * This screening pathway is an operational safety net designed to expedite care.
 * It is NOT an autonomous diagnostic tool. Immediate clinician evaluation is mandatory.
 * This academic prototype has not undergone clinical validation.
 */

export const RED_FLAG_SYMPTOMS = [
  'chest pain',
  'difficulty breathing',
  'shortness of breath',
  'unconscious',
  'unresponsive',
  'stroke',
  'facial drooping',
  'slurred speech',
  'anaphylaxis',
  'severe bleeding',
  'seizure',
  'severe head injury',
];

export function evaluateEmergencyIntake(vitals = {}, symptoms = [], chiefComplaint = '') {
  const reasons = [];
  // isEmergency is ONLY set true by objective physiological findings (vitals, mental status).
  // Symptom text matches alone go into reasons but do NOT set isEmergency.
  let vitalEmergency = false;
  const symptomWarnings = [];

  const spo2 = Number(vitals.spo2);
  const sbp = Number(vitals.systolicBP);
  const dbp = Number(vitals.diastolicBP);
  const hr = Number(vitals.heartRate);
  const temp = Number(vitals.temperature);

  // 1. Oxygen Saturation (SpO2) — objective vital: sets emergency flag
  if (spo2 > 0 && spo2 < 90) {
    vitalEmergency = true;
    if (spo2 <= 70) {
      reasons.push(
        `PROFOUND CRITICAL HYPOXIA / SENSOR RECHECK: SpO2 at ${spo2}% (<90%) indicates life-threatening hypoxemia. Immediate emergency assessment and acute oxygenation required. Staff must verify probe placement and waveform on an alternate site to rule out measurement artifact without delaying supportive care.`
      );
    } else {
      reasons.push(
        `CRITICAL HYPOXIA: SpO2 at ${spo2}% (<90%) indicates severe arterial desaturation. Immediate physician evaluation required.`
      );
    }
  } else if (spo2 >= 90 && spo2 < 94) {
    reasons.push(`Sub-optimal SpO2 (${spo2}%) requires close observation.`);
  }

  // 2. Blood Pressure — objective vital: sets emergency flag
  if (sbp >= 180) {
    vitalEmergency = true;
    reasons.push(`HYPERTENSIVE CRISIS: Systolic BP ${sbp} mmHg (≥180 mmHg) risks acute organ damage.`);
  } else if (sbp > 0 && sbp < 90) {
    vitalEmergency = true;
    reasons.push(`HYPOTENSIVE SHOCK RISK: Systolic BP ${sbp} mmHg (<90 mmHg) indicates hemodynamic collapse.`);
  }

  if (dbp >= 110) {
    vitalEmergency = true;
    reasons.push(`HYPERTENSIVE EMERGENCY: Diastolic BP ${dbp} mmHg (≥110 mmHg).`);
  }

  // 3. Heart Rate — objective vital: sets emergency flag
  if (hr > 130) {
    vitalEmergency = true;
    reasons.push(`SEVERE TACHYCARDIA: Pulse rate ${hr} bpm (>130 bpm).`);
  } else if (hr > 0 && hr < 45) {
    vitalEmergency = true;
    reasons.push(`CRITICAL BRADYCARDIA: Pulse rate ${hr} bpm (<45 bpm).`);
  }

  // 4. Core Temperature — informational warning only (no emergency flag without other criteria)
  if (temp >= 104) {
    reasons.push(`HYPERPYREXIA: Body temperature ${temp}°F (≥104°F).`);
  }

  // 5. Red-Flag Symptoms — warning only.
  // Symptom self-report alone does NOT trigger isEmergency (no objective vital confirmation).
  // The UI shows this as a prominent warning banner to prompt clinical review.
  // Exception: reported 'unconscious' or 'unresponsive' implies altered mental status.
  const combinedText = `${chiefComplaint} ${symptoms.join(' ')}`.toLowerCase();
  for (const trigger of RED_FLAG_SYMPTOMS) {
    if (combinedText.includes(trigger)) {
      if (trigger === 'unconscious' || trigger === 'unresponsive') {
        // Reported loss of consciousness is treated as an emergency indicator
        vitalEmergency = true;
        reasons.push(`EMERGENCY PRESENTATION: Reported '${trigger.toUpperCase()}' — immediate clinical evaluation required.`);
      } else {
        // All other red-flag symptoms: warn and recommend priority, do NOT auto-escalate
        symptomWarnings.push(
          `RED-FLAG SYMPTOM REPORTED: '${trigger.toUpperCase()}' — requires prompt clinical assessment. Verify with objective vitals.`
        );
      }
    }
  }

  // Combine: symptom warnings are appended after vital reasons
  const allReasons = [...reasons, ...symptomWarnings];
  const isEmergency = vitalEmergency;
  const hasSymptomWarning = symptomWarnings.length > 0;

  return {
    isEmergency,
    escalationLevel: isEmergency
      ? 'IMMEDIATE_ESCALATION'
      : (hasSymptomWarning || allReasons.length > 0)
        ? 'HIGH_PRIORITY'
        : 'STANDARD',
    reasons: allReasons,
    actionRequired: isEmergency
      ? 'IMMEDIATE CLINICAL ESCALATION REQUIRED: Patient meets clinical red-flag criteria. Alert the on-duty emergency physician immediately and transfer to resuscitation bay. Do NOT retain in general outpatient queue. Clinical staff must recheck any potentially discordant vitals (including pulse oximeter probe placement) without delaying appropriate care. Emergency warnings cannot be overridden by ML scoring or missing medical history; the qualified clinician remains responsible for final clinical decisions.'
      : hasSymptomWarning
        ? 'PRIORITY CLINICAL REVIEW RECOMMENDED: Patient has reported a high-acuity symptom. Verify with objective vital signs and prompt physician assessment. Symptom self-report alone does not constitute an emergency override — vitals remain the primary clinical decision point.'
        : 'Standard outpatient queue triage pathway.',
    clinicalNotice: 'Preliminary operational screening safety net. Qualified clinician review mandatory. This academic prototype has not undergone clinical validation.',
  };
}
