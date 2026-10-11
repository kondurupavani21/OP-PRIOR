/**
 * priorityCalculator.js
 * Simulated Patient Triage & Priority Scoring Algorithm
 * 
 * DISCLAIMER:
 * This is a transparent frontend demonstration algorithm for educational/hackathon/project use.
 * It is NOT medically validated or intended for clinical diagnosis.
 */

export function calculatePriority(patientData) {
  let score = 20; // Base score for any patient presenting at outpatient clinic
  const factors = [];

  const age = Number(patientData.age) || 0;
  const temp = Number(patientData.temperature) || 98.6;
  const hr = Number(patientData.heartRate) || 75;
  const spo2 = Number(patientData.spo2) || 98;
  const sugar = Number(patientData.sugarLevel) || 100;
  const bpString = String(patientData.bloodPressure || '120/80').trim();
  const symptoms = Array.isArray(patientData.symptoms) ? patientData.symptoms : (patientData.symptoms ? [patientData.symptoms] : []);
  const diseases = Array.isArray(patientData.previousDiseases) ? patientData.previousDiseases : (patientData.previousDiseases ? [patientData.previousDiseases] : []);

  // 1. Oxygen Saturation (SpO2)
  if (spo2 > 0) {
    if (spo2 < 90) {
      score += 32;
      factors.push({
        title: 'Severe Hypoxia',
        description: `SpO2 at critical level (${spo2}%)`,
        points: '+32',
        level: 'critical',
      });
    } else if (spo2 <= 94) {
      score += 18;
      factors.push({
        title: 'Mild-Moderate Hypoxia',
        description: `SpO2 sub-optimal (${spo2}%)`,
        points: '+18',
        level: 'warning',
      });
    }
  }

  // 2. Heart Rate (Pulse bpm)
  if (hr > 0) {
    if (hr > 125 || hr < 45) {
      score += 24;
      factors.push({
        title: 'Severe Tachycardia / Bradycardia',
        description: `Abnormal pulse (${hr} bpm)`,
        points: '+24',
        level: 'critical',
      });
    } else if (hr > 100 || hr < 55) {
      score += 12;
      factors.push({
        title: 'Elevated Heart Rate',
        description: `Resting pulse elevated (${hr} bpm)`,
        points: '+12',
        level: 'warning',
      });
    }
  }

  // 3. Blood Pressure
  let systolic = 120;
  let diastolic = 80;
  if (bpString.includes('/')) {
    const parts = bpString.split('/');
    systolic = parseInt(parts[0], 10) || 120;
    diastolic = parseInt(parts[1], 10) || 80;
  }
  if (systolic >= 180 || diastolic >= 110) {
    score += 26;
    factors.push({
      title: 'Hypertensive Crisis Range',
      description: `Blood pressure at ${systolic}/${diastolic} mmHg`,
      points: '+26',
      level: 'critical',
    });
  } else if (systolic >= 150 || diastolic >= 95) {
    score += 16;
    factors.push({
      title: 'Stage 2 Hypertension',
      description: `Elevated BP (${systolic}/${diastolic} mmHg)`,
      points: '+16',
      level: 'warning',
    });
  } else if (systolic < 90 && systolic > 0) {
    score += 22;
    factors.push({
      title: 'Hypotension / Shock Risk',
      description: `Systolic BP low (${systolic} mmHg)`,
      points: '+22',
      level: 'critical',
    });
  }

  // 4. Body Temperature
  if (temp > 0) {
    if (temp >= 103) {
      score += 18;
      factors.push({
        title: 'High Pyrexia / Severe Fever',
        description: `Body temperature at ${temp}°F`,
        points: '+18',
        level: 'critical',
      });
    } else if (temp >= 100.4) {
      score += 10;
      factors.push({
        title: 'Febrile State',
        description: `Elevated temperature (${temp}°F)`,
        points: '+10',
        level: 'warning',
      });
    }
  }

  // 5. Blood Sugar (mg/dL)
  if (sugar > 0) {
    if (sugar < 65) {
      score += 20;
      factors.push({
        title: 'Severe Hypoglycemia',
        description: `Blood glucose low (${sugar} mg/dL)`,
        points: '+20',
        level: 'critical',
      });
    } else if (sugar > 280) {
      score += 15;
      factors.push({
        title: 'Severe Hyperglycemia',
        description: `Blood glucose high (${sugar} mg/dL)`,
        points: '+15',
        level: 'warning',
      });
    }
  }

  // 6. High-risk Symptoms
  const symptomKeywords = symptoms.map((s) => String(s).toLowerCase());
  const criticalSymptomMap = [
    { key: 'chest pain', title: 'Acute Chest Pain', pts: 25 },
    { key: 'shortness of breath', title: 'Severe Dyspnea', pts: 22 },
    { key: 'breathlessness', title: 'Dyspnea / Air Hunger', pts: 22 },
    { key: 'stroke', title: 'Acute Neurological Deficit', pts: 30 },
    { key: 'unconscious', title: 'Altered Consciousness', pts: 35 },
    { key: 'fainting', title: 'Syncope / Loss of Consciousness', pts: 20 },
    { key: 'severe bleeding', title: 'Acute Hemorrhage', pts: 28 },
    { key: 'trauma', title: 'High-Impact Trauma', pts: 25 },
    { key: 'seizure', title: 'Active / Recent Seizure', pts: 25 },
    { key: 'severe headache', title: 'Thunderclap / Severe Cephalea', pts: 15 },
  ];

  for (const crit of criticalSymptomMap) {
    if (symptomKeywords.some((s) => s.includes(crit.key))) {
      score += crit.pts;
      factors.push({
        title: crit.title,
        description: `Reported critical presenting symptom: "${crit.key}"`,
        points: `+${crit.pts}`,
        level: 'critical',
      });
      break; // count primary critical symptom to prevent artificial runaway
    }
  }

  // 7. Vulnerable Age Categories
  if (age >= 65) {
    score += 10;
    factors.push({
      title: 'Geriatric Age Consideration',
      description: `Patient age is ${age} years (elevated physiological risk)`,
      points: '+10',
      level: 'info',
    });
  } else if (age > 0 && age <= 5) {
    score += 10;
    factors.push({
      title: 'Pediatric Patient',
      description: `Pediatric patient (${age} yrs)`,
      points: '+10',
      level: 'info',
    });
  }

  // 8. Chronic Disease / Medical History Comorbidities
  const diseaseKeywords = diseases.map((d) => String(d).toLowerCase());
  const comorbidityMap = [
    { key: 'cardiac', label: 'Chronic Cardiovascular Disease', pts: 10 },
    { key: 'heart', label: 'History of Cardiac Illness', pts: 10 },
    { key: 'asthma', label: 'Severe Bronchial Asthma / COPD', pts: 8 },
    { key: 'copd', label: 'Chronic Obstructive Pulmonary Disease', pts: 10 },
    { key: 'kidney', label: 'Chronic Kidney Disease', pts: 8 },
    { key: 'diabetes', label: 'Diabetes Mellitus Comorbidity', pts: 5 },
    { key: 'hypertension', label: 'Chronic Arterial Hypertension', pts: 5 },
  ];

  let chronicPtsAdded = 0;
  for (const com of comorbidityMap) {
    if (diseaseKeywords.some((d) => d.includes(com.key))) {
      if (chronicPtsAdded < 15) { // cap chronic disease impact
        score += com.pts;
        chronicPtsAdded += com.pts;
        factors.push({
          title: com.label,
          description: 'Documented medical history comorbidity',
          points: `+${com.pts}`,
          level: 'info',
        });
      }
    }
  }

  // Clamp final score to 5 - 100
  const finalScore = Math.min(100, Math.max(5, Math.round(score)));

  let severity = 'LOW';
  let emergencyRisk = 'NO';

  if (finalScore >= 80) {
    severity = 'HIGH';
    emergencyRisk = 'YES';
  } else if (finalScore >= 50) {
    severity = 'MEDIUM';
    emergencyRisk = 'NO';
  } else {
    severity = 'LOW';
    emergencyRisk = 'NO';
  }

  return {
    priorityScore: finalScore,
    severity,
    emergencyRisk,
    factors: factors.length > 0 ? factors : [
      {
        title: 'Stable Vital Signs',
        description: 'Vitals and presenting symptoms are within routine parameters',
        points: 'Baseline',
        level: 'info',
      }
    ],
    timestamp: new Date().toISOString(),
    algorithmVersion: 'MedQueue-Heuristic-v2.1',
  };
}
