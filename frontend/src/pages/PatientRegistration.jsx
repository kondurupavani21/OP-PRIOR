import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { calculatePriority } from '../utils/priorityCalculator';
import { generateNextPatientId, findPatientByPhone, normalizePhone } from '../utils/patientUtils';
import { evaluateEmergencyIntake } from '../utils/emergencyScreening';
import MedicalDocumentUpload from '../components/medical/MedicalDocumentUpload';
import api from '../services/api';
import {
  UserPlus,
  RotateCcw,
  HeartPulse,
  Activity,
  Thermometer,
  Wind,
  Droplet,
  Search,
  CheckCircle,
  AlertCircle,
  AlertTriangle,
  ShieldAlert,
  History,
  Info,
  Phone,
  User,
  Calendar,
  Building2,
  Stethoscope,
  Pill,
  Plus,
  Trash2,
  FileText,
  UploadCloud,
} from 'lucide-react';

const COMMON_SYMPTOMS = [
  'Fever',
  'Cough',
  'Chest Pain',
  'Shortness of Breath',
  'Dizziness',
  'Severe Headache',
  'Abdominal Pain',
  'Vomiting',
  'Fatigue',
  'High Blood Pressure',
  'Trauma / Fall Injury',
  'Allergic Reaction',
];

const CHRONIC_CONDITIONS = [
  'Hypertension',
  'Diabetes Mellitus',
  'Cardiovascular Disease',
  'Asthma / COPD',
  'Chronic Kidney Disease',
  'Thyroid Disorder',
  'None',
];

export default function PatientRegistration() {
  const navigate = useNavigate();
  const { patients, registerPatientRecord, addToast } = useApp();

  // Form State
  const [patientName, setPatientName] = useState('');
  const [age, setAge] = useState('');
  const [gender, setGender] = useState('Male');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [patientType, setPatientType] = useState('New Card / First Visit');
  const [existingPatientMatch, setExistingPatientMatch] = useState(null);

  // Current Encounter Symptoms
  const [chiefComplaint, setChiefComplaint] = useState('');
  const [symptomDuration, setSymptomDuration] = useState('1 day');
  const [selectedSymptoms, setSelectedSymptoms] = useState([]);
  const [customSymptom, setCustomSymptom] = useState('');

  // Vital Signs
  const [temperature, setTemperature] = useState('');
  const [heartRate, setHeartRate] = useState('');
  const [systolicBP, setSystolicBP] = useState('');
  const [diastolicBP, setDiastolicBP] = useState('');
  const [spo2, setSpo2] = useState('');
  const [sugarLevel, setSugarLevel] = useState('');

  // Previous Consultation Inquiry (Phase 2 Requirement)
  const [hasConsultedBefore, setHasConsultedBefore] = useState('No'); // 'Yes', 'No', 'Not sure'
  const [previousConsultations, setPreviousConsultations] = useState([
    {
      id: '1',
      facilityName: '',
      doctorName: '',
      consultationDate: '',
      previousSymptoms: '',
      previousDiagnosis: '',
      previousInvestigations: '',
      treatmentPrescribed: '',
      medicinesTaken: '',
      durationOfTreatment: '',
      treatmentResponse: 'UNCHANGED', // 'IMPROVED', 'UNCHANGED', 'WORSENED', 'NOT_SURE'
      sideEffects: '',
    },
  ]);

  // Medical History
  const [selectedDiseases, setSelectedDiseases] = useState([]);
  const [customHistory, setCustomHistory] = useState('');

  // Provisional patient ID for attaching document uploads
  const targetPatientId = useMemo(() => {
    return existingPatientMatch
      ? existingPatientMatch.patientId
      : `PAT-${1001 + patients.length}`;
  }, [existingPatientMatch, patients.length]);

  // Validation / UI
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Real-time Phone Number Lookup for Existing Patient Detection
  useEffect(() => {
    const clean = normalizePhone(phoneNumber);
    if (clean.length >= 7) {
      const match = findPatientByPhone(patients, clean);
      if (match) {
        setExistingPatientMatch(match);
        setPatientType('Existing Patient');
        if (!patientName) setPatientName(match.patientName);
        if (!age) setAge(match.age);
        if (match.gender) setGender(match.gender);
        if (match.previousDiseases && match.previousDiseases.length > 0) {
          setSelectedDiseases(match.previousDiseases);
        }
      } else {
        setExistingPatientMatch(null);
        if (patientType === 'Existing Patient' && !clean) {
          setPatientType('New Card / First Visit');
        }
      }
    } else {
      setExistingPatientMatch(null);
    }
  }, [phoneNumber, patients]);

  // Synchronous Clinical Emergency Screening
  const emergencyScreening = useMemo(() => {
    return evaluateEmergencyIntake(
      {
        spo2,
        systolicBP,
        diastolicBP,
        heartRate,
        temperature,
      },
      [...selectedSymptoms, ...(customSymptom.trim() ? [customSymptom.trim()] : [])]
    );
  }, [spo2, systolicBP, diastolicBP, heartRate, temperature, selectedSymptoms, customSymptom]);

  const toggleSymptom = (sym) => {
    setSelectedSymptoms((prev) =>
      prev.includes(sym) ? prev.filter((s) => s !== sym) : [...prev, sym]
    );
  };

  const addCustomSymptom = () => {
    if (customSymptom.trim() && !selectedSymptoms.includes(customSymptom.trim())) {
      setSelectedSymptoms((prev) => [...prev, customSymptom.trim()]);
      setCustomSymptom('');
    }
  };

  const toggleDisease = (dis) => {
    if (dis === 'None') {
      setSelectedDiseases(['None']);
      return;
    }
    setSelectedDiseases((prev) => {
      const withoutNone = prev.filter((d) => d !== 'None');
      return withoutNone.includes(dis)
        ? withoutNone.filter((d) => d !== dis)
        : [...withoutNone, dis];
    });
  };

  // Previous Consultation form helpers
  const addConsultationRow = () => {
    setPreviousConsultations((prev) => [
      ...prev,
      {
        id: String(Date.now()),
        facilityName: '',
        doctorName: '',
        consultationDate: '',
        previousSymptoms: '',
        previousDiagnosis: '',
        previousInvestigations: '',
        treatmentPrescribed: '',
        medicinesTaken: '',
        durationOfTreatment: '',
        treatmentResponse: 'UNCHANGED',
        sideEffects: '',
      },
    ]);
  };

  const updateConsultationRow = (id, field, value) => {
    setPreviousConsultations((prev) =>
      prev.map((c) => (c.id === id ? { ...c, [field]: value } : c))
    );
  };

  const removeConsultationRow = (id) => {
    setPreviousConsultations((prev) => prev.filter((c) => c.id !== id));
  };

  const handleReset = () => {
    setPatientName('');
    setAge('');
    setGender('Male');
    setPhoneNumber('');
    setPatientType('New Card / First Visit');
    setExistingPatientMatch(null);
    setChiefComplaint('');
    setSymptomDuration('1 day');
    setSelectedSymptoms([]);
    setCustomSymptom('');
    setTemperature('');
    setHeartRate('');
    setSystolicBP('');
    setDiastolicBP('');
    setSpo2('');
    setSugarLevel('');
    setHasConsultedBefore('No');
    setPreviousConsultations([
      {
        id: '1',
        facilityName: '',
        doctorName: '',
        consultationDate: '',
        previousSymptoms: '',
        previousDiagnosis: '',
        previousInvestigations: '',
        treatmentPrescribed: '',
        medicinesTaken: '',
        durationOfTreatment: '',
        treatmentResponse: 'UNCHANGED',
        sideEffects: '',
      },
    ]);
    setSelectedDiseases([]);
    setCustomHistory('');
    setErrors({});
  };

  const validate = () => {
    const err = {};
    if (!patientName.trim()) err.patientName = 'Patient name is required.';
    if (!age || isNaN(age) || Number(age) < 0 || Number(age) > 125) {
      err.age = 'Please enter a valid age (0–125).';
    }
    if (!phoneNumber.trim() || normalizePhone(phoneNumber).length < 7) {
      err.phoneNumber = 'A valid phone number is required (min. 7 digits).';
    }
    if (selectedSymptoms.length === 0 && !chiefComplaint.trim()) {
      err.symptoms = 'Please select or enter at least one presenting symptom or chief complaint.';
    }
    if (temperature && (isNaN(temperature) || Number(temperature) < 90 || Number(temperature) > 110)) {
      err.temperature = 'Valid temp: 90°F–110°F.';
    }
    if (heartRate && (isNaN(heartRate) || Number(heartRate) < 30 || Number(heartRate) > 250)) {
      err.heartRate = 'Valid HR: 30–250 bpm.';
    }
    if (spo2 && (isNaN(spo2) || Number(spo2) < 50 || Number(spo2) > 100)) {
      err.spo2 = 'Valid SpO2: 50%–100%.';
    }
    if (sugarLevel && (isNaN(sugarLevel) || Number(sugarLevel) < 20 || Number(sugarLevel) > 800)) {
      err.sugarLevel = 'Valid sugar: 20–800 mg/dL.';
    }
    if (systolicBP && (isNaN(systolicBP) || Number(systolicBP) < 50 || Number(systolicBP) > 260)) {
      err.bloodPressure = 'Valid systolic: 50–260.';
    }
    if (diastolicBP && (isNaN(diastolicBP) || Number(diastolicBP) < 30 || Number(diastolicBP) > 160)) {
      err.bloodPressure = 'Valid diastolic: 30–160.';
    }

    setErrors(err);
    return Object.keys(err).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    setIsSubmitting(true);

    const bp = systolicBP && diastolicBP ? `${systolicBP}/${diastolicBP}` : systolicBP ? `${systolicBP}/80` : '120/80';
    const assignedId = existingPatientMatch
      ? existingPatientMatch.patientId
      : generateNextPatientId(patients);

    const effectiveChiefComplaint = chiefComplaint.trim() || (selectedSymptoms.length > 0 ? selectedSymptoms[0] : 'General Consultation');

    // Build previous consultations list
    const cleanPrevConsultations = hasConsultedBefore === 'Yes'
      ? previousConsultations
          .filter((c) => c.facilityName.trim() || c.previousDiagnosis.trim() || c.treatmentPrescribed.trim() || c.medicinesTaken.trim())
          .map((c) => ({
            facility_name: c.facilityName.trim() || 'External Clinic',
            doctor_name: c.doctorName.trim() || null,
            consultation_date: c.consultationDate || null,
            previous_symptoms: c.previousSymptoms ? c.previousSymptoms.split(',').map((s) => s.trim()).filter(Boolean) : [],
            previous_diagnosis: c.previousDiagnosis.trim() || null,
            previous_investigations: c.previousInvestigations ? c.previousInvestigations.split(',').map((s) => s.trim()).filter(Boolean) : [],
            treatment_prescribed: c.treatmentPrescribed.trim() || null,
            medicines_taken: c.medicinesTaken ? c.medicinesTaken.split(',').map((s) => s.trim()).filter(Boolean) : [],
            duration_of_treatment: c.durationOfTreatment.trim() || null,
            treatment_response: c.treatmentResponse || 'UNCHANGED',
            side_effects_reported: c.sideEffects.trim() || null,
            source_provenance: 'PATIENT_REPORTED',
          }))
      : [];

    // Patient record
    const patientData = {
      patientId: assignedId,
      patientName: patientName.trim(),
      age: Number(age),
      gender,
      phoneNumber: phoneNumber.trim(),
      patientType: existingPatientMatch ? 'Existing Patient' : patientType,
      chiefComplaint: effectiveChiefComplaint,
      symptomDuration: symptomDuration.trim() || '1 day',
      symptoms: selectedSymptoms.length > 0 ? selectedSymptoms : [effectiveChiefComplaint],
      temperature: temperature ? Number(temperature) : 98.6,
      heartRate: heartRate ? Number(heartRate) : 75,
      bloodPressure: bp,
      spo2: spo2 ? Number(spo2) : 98,
      sugarLevel: sugarLevel ? Number(sugarLevel) : 100,
      previousDiseases: selectedDiseases,
      customHistory: customHistory.trim(),
      hasConsultedBefore,
      previousConsultations: cleanPrevConsultations,
      visits: existingPatientMatch ? existingPatientMatch.visits || [] : [],
    };

    // Calculate priority
    const triageResult = calculatePriority(patientData);

    // Register locally & queue immediately
    registerPatientRecord(patientData, triageResult);

    // Record previous consultations in backend asynchronously
    if (cleanPrevConsultations.length > 0) {
      for (const pcon of cleanPrevConsultations) {
        api.recordPreviousConsultation(assignedId, {
          patient_code: assignedId,
          ...pcon,
        }).catch((err) => console.info('Note on recording previous consultation:', err.message));
      }
    }

    setIsSubmitting(false);

    if (existingPatientMatch) {
      addToast(`Existing patient ${patientName} (${assignedId}) registered with Priority Score ${triageResult.priorityScore}!`, 'info');
    } else {
      addToast(`New patient ${patientName} registered as ${assignedId} with Priority Score ${triageResult.priorityScore}!`, 'success');
    }

    navigate(`/priority/${assignedId}`);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Page Title & Intro */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
            Patient Outpatient Registration & Clinical Triage
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Capture patient intake, previous external consultations, medical documents, and run the emergency screening pathway.
          </p>
        </div>

        <button
          type="button"
          onClick={handleReset}
          className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-100 text-xs font-semibold transition cursor-pointer self-start"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Clear Form</span>
        </button>
      </div>

      {/* EXISTING PATIENT DETECTION BANNER */}
      {existingPatientMatch && (
        <div className="p-4 rounded-2xl bg-purple-50 border border-purple-200 flex items-start justify-between gap-3 animate-in fade-in">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-xl bg-purple-100 text-purple-700 shrink-0">
              <History className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h4 className="text-sm font-bold text-purple-900">
                  Existing Patient Identified!
                </h4>
                <span className="font-mono text-xs font-bold bg-purple-200/80 text-purple-800 px-2 py-0.5 rounded">
                  {existingPatientMatch.patientId}
                </span>
              </div>
              <p className="text-xs text-purple-700 mt-1">
                Matched phone number to <strong>{existingPatientMatch.patientName}</strong> with {existingPatientMatch.visits?.length || 0} recorded previous visits.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* SYNCHRONOUS EMERGENCY ESCALATION ALERT BANNER */}
      {emergencyScreening.isEmergency && (
        <div className="p-5 rounded-2xl bg-rose-50 border-2 border-rose-500 shadow-md flex items-start gap-4 animate-in fade-in">
          <div className="p-2.5 rounded-xl bg-rose-600 text-white shrink-0 mt-0.5 animate-pulse">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div className="space-y-2 flex-1">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-black tracking-wider bg-rose-600 text-white uppercase">
                Clinical Emergency Warning
              </span>
              <span className="text-xs font-semibold text-rose-700">Immediate Action Required</span>
            </div>
            <p className="text-sm font-bold text-rose-950">
              {emergencyScreening.actionRequired}
            </p>
            <div className="space-y-1 pt-1 border-t border-rose-200">
              <p className="text-xs font-semibold text-rose-800">Critical Clinical Triggers Identified:</p>
              <ul className="list-disc list-inside space-y-0.5 text-xs text-rose-900 font-medium">
                {emergencyScreening.reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
            <p className="text-[11px] text-rose-600/90 italic pt-1">
              Safety Net Protocol: Standardized clinical warning pathway. Do not delay emergency physician review for administrative document uploads.
            </p>
          </div>
        </div>
      )}

      {/* REGISTRATION FORM */}
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* SECTION 1: PERSONAL INFORMATION */}
        <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <User className="w-4 h-4 text-blue-600" />
            <h3 className="text-sm font-bold text-slate-900">
              1. Patient Personal Information
            </h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Phone Number */}
            <div className="sm:col-span-2">
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Phone Number (Identification Key) *
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Phone className="w-4 h-4" />
                </div>
                <input
                  type="tel"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  placeholder="e.g. 9876543210"
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 text-sm text-slate-800 focus:outline-hidden focus:border-blue-500 focus:ring-3 focus:ring-blue-500/10 transition"
                />
              </div>
              {errors.phoneNumber && (
                <p className="text-[11px] text-rose-500 mt-1">{errors.phoneNumber}</p>
              )}
            </div>

            {/* Patient Name */}
            <div className="sm:col-span-2">
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Patient Full Name *
              </label>
              <input
                type="text"
                value={patientName}
                onChange={(e) => setPatientName(e.target.value)}
                placeholder="Enter patient full name"
                className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm text-slate-800 focus:outline-hidden focus:border-blue-500 focus:ring-3 focus:ring-blue-500/10 transition"
              />
              {errors.patientName && (
                <p className="text-[11px] text-rose-500 mt-1">{errors.patientName}</p>
              )}
            </div>

            {/* Age */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Age (Years) *
              </label>
              <input
                type="number"
                value={age}
                onChange={(e) => setAge(e.target.value)}
                placeholder="Age"
                min="0"
                max="125"
                className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm text-slate-800 focus:outline-hidden focus:border-blue-500 focus:ring-3 focus:ring-blue-500/10 transition"
              />
              {errors.age && (
                <p className="text-[11px] text-rose-500 mt-1">{errors.age}</p>
              )}
            </div>

            {/* Gender */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Gender *
              </label>
              <select
                value={gender}
                onChange={(e) => setGender(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm text-slate-800 focus:outline-hidden focus:border-blue-500 bg-white"
              >
                <option value="Male">Male</option>
                <option value="Female">Female</option>
                <option value="Other">Other</option>
              </select>
            </div>

            {/* Patient Type */}
            <div className="sm:col-span-2">
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Registration Type
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setPatientType('New Card / First Visit')}
                  className={`py-2 px-3 text-xs font-semibold rounded-xl border transition cursor-pointer ${
                    patientType === 'New Card / First Visit' && !existingPatientMatch
                      ? 'bg-blue-50 border-blue-600 text-blue-700'
                      : 'border-slate-200 text-slate-600 hover:border-slate-300'
                  }`}
                >
                  New Card / First Visit
                </button>
                <button
                  type="button"
                  onClick={() => setPatientType('Existing Patient')}
                  className={`py-2 px-3 text-xs font-semibold rounded-xl border transition cursor-pointer ${
                    patientType === 'Existing Patient' || existingPatientMatch
                      ? 'bg-purple-50 border-purple-600 text-purple-700'
                      : 'border-slate-200 text-slate-600 hover:border-slate-300'
                  }`}
                >
                  Existing Patient
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* SECTION 2: CURRENT PRESENTING SYMPTOMS & CHIEF COMPLAINT */}
        <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-blue-600" />
              <h3 className="text-sm font-bold text-slate-900">
                2. Current Presentation & Symptoms *
              </h3>
            </div>
            <span className="text-xs text-slate-400">
              {selectedSymptoms.length} symptom(s) tagged
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="sm:col-span-2">
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Primary Chief Complaint
              </label>
              <input
                type="text"
                value={chiefComplaint}
                onChange={(e) => setChiefComplaint(e.target.value)}
                placeholder="e.g. Recurrent fever with persistent dry cough and breathlessness"
                className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-xs text-slate-800 focus:outline-hidden focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Symptom Duration
              </label>
              <select
                value={symptomDuration}
                onChange={(e) => setSymptomDuration(e.target.value)}
                className="w-full px-3 py-2.5 rounded-xl border border-slate-200 text-xs text-slate-800 focus:outline-hidden focus:border-blue-500 bg-white"
              >
                <option value="1 day">1 day</option>
                <option value="2-3 days">2-3 days</option>
                <option value="1 week">1 week</option>
                <option value="2 weeks">2 weeks</option>
                <option value="1 month+">1 month or more</option>
              </select>
            </div>
          </div>

          {errors.symptoms && (
            <p className="text-[11px] text-rose-500">{errors.symptoms}</p>
          )}

          {/* Symptom Quick Chips */}
          <div>
            <span className="block text-[11px] font-semibold text-slate-500 mb-1.5">
              Associated Presenting Symptoms:
            </span>
            <div className="flex flex-wrap gap-2">
              {COMMON_SYMPTOMS.map((sym) => {
                const isSelected = selectedSymptoms.includes(sym);
                const isCritical = ['Chest Pain', 'Shortness of Breath', 'Trauma / Fall Injury'].includes(sym);

                return (
                  <button
                    key={sym}
                    type="button"
                    onClick={() => toggleSymptom(sym)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-medium border transition cursor-pointer flex items-center gap-1.5 ${
                      isSelected
                        ? isCritical
                          ? 'bg-rose-100 border-rose-400 text-rose-800 font-bold'
                          : 'bg-blue-100 border-blue-400 text-blue-800 font-bold'
                        : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    <span>{sym}</span>
                    {isSelected && <span className="text-xs">✓</span>}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Custom Symptom Input */}
          <div className="flex gap-2 pt-2">
            <input
              type="text"
              value={customSymptom}
              onChange={(e) => setCustomSymptom(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  addCustomSymptom();
                }
              }}
              placeholder="Or add other specific symptom..."
              className="flex-1 px-4 py-2 rounded-xl border border-slate-200 text-xs text-slate-800 focus:outline-hidden focus:border-blue-500 transition"
            />
            <button
              type="button"
              onClick={addCustomSymptom}
              className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition cursor-pointer"
            >
              Add
            </button>
          </div>
        </div>

        {/* SECTION 3: PREVIOUS CONSULTATION FOR THIS PROBLEM (Phase 2 Requirement) */}
        <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-5">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <Stethoscope className="w-4 h-4 text-indigo-600" />
            <h3 className="text-sm font-bold text-slate-900">
              3. Previous Consultations for Current Problem
            </h3>
          </div>

          <div className="bg-indigo-50/50 p-4 rounded-xl border border-indigo-100 space-y-3">
            <label className="block text-xs font-bold text-indigo-950">
              Have you consulted another doctor or hospital for this current problem? *
            </label>
            <div className="flex flex-wrap gap-2.5">
              {['Yes', 'No', 'Not sure'].map((opt) => (
                <button
                  key={opt}
                  type="button"
                  onClick={() => setHasConsultedBefore(opt)}
                  className={`px-4 py-2 rounded-xl text-xs font-bold border transition cursor-pointer ${
                    hasConsultedBefore === opt
                      ? 'bg-indigo-600 text-white border-indigo-600 shadow-xs'
                      : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  {opt}
                </button>
              ))}
            </div>
            <p className="text-[11px] text-slate-500">
              Captures prior diagnosis, prescribed drugs, and whether symptoms improved, remained unchanged, or worsened. All details are optional if unknown.
            </p>
          </div>

          {/* Conditional Previous Consultation Form */}
          {hasConsultedBefore === 'Yes' && (
            <div className="space-y-4 pt-2 animate-in fade-in">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-800">
                  Documented / Patient-Reported External Consultations
                </span>
                <button
                  type="button"
                  onClick={addConsultationRow}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-indigo-50 text-indigo-700 hover:bg-indigo-100 text-xs font-semibold transition cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add Another Consultation</span>
                </button>
              </div>

              {previousConsultations.map((pcon, idx) => (
                <div
                  key={pcon.id}
                  className="p-5 rounded-2xl bg-slate-50 border border-slate-200 space-y-4 relative"
                >
                  <div className="flex items-center justify-between pb-2 border-b border-slate-200">
                    <span className="font-bold text-xs text-slate-800 flex items-center gap-2">
                      <Building2 className="w-3.5 h-3.5 text-indigo-600" />
                      <span>Previous Consultation #{idx + 1}</span>
                    </span>
                    {previousConsultations.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeConsultationRow(pcon.id)}
                        className="p-1 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition cursor-pointer"
                        title="Remove consultation"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {/* Facility */}
                    <div>
                      <label className="block text-[10px] font-semibold text-slate-500 mb-1">
                        Previous Hospital or Clinic
                      </label>
                      <input
                        type="text"
                        value={pcon.facilityName}
                        onChange={(e) => updateConsultationRow(pcon.id, 'facilityName', e.target.value)}
                        placeholder="e.g. Apollo Clinic / City Govt Hospital"
                        className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs bg-white focus:outline-hidden focus:border-indigo-500"
                      />
                    </div>

                    {/* Doctor */}
                    <div>
                      <label className="block text-[10px] font-semibold text-slate-500 mb-1">
                        Previous Doctor Name (if known)
                      </label>
                      <input
                        type="text"
                        value={pcon.doctorName}
                        onChange={(e) => updateConsultationRow(pcon.id, 'doctorName', e.target.value)}
                        placeholder="e.g. Dr. K. Rao"
                        className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs bg-white focus:outline-hidden focus:border-indigo-500"
                      />
                    </div>

                    {/* Consultation Date */}
                    <div>
                      <label className="block text-[10px] font-semibold text-slate-500 mb-1">
                        Consultation Date (Approximate)
                      </label>
                      <input
                        type="date"
                        value={pcon.consultationDate}
                        onChange={(e) => updateConsultationRow(pcon.id, 'consultationDate', e.target.value)}
                        className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs bg-white focus:outline-hidden focus:border-indigo-500"
                      />
                    </div>

                    {/* Previous Diagnosis */}
                    <div className="sm:col-span-2">
                      <label className="block text-[10px] font-semibold text-slate-500 mb-1">
                        Previous Diagnosis (as documented or communicated)
                      </label>
                      <input
                        type="text"
                        value={pcon.previousDiagnosis}
                        onChange={(e) => updateConsultationRow(pcon.id, 'previousDiagnosis', e.target.value)}
                        placeholder="e.g. Viral Bronchitis, Acute Gastritis"
                        className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs bg-white focus:outline-hidden focus:border-indigo-500"
                      />
                    </div>

                    {/* Response to Treatment */}
                    <div>
                      <label className="block text-[10px] font-semibold text-slate-500 mb-1">
                        Response to Treatment *
                      </label>
                      <select
                        value={pcon.treatmentResponse}
                        onChange={(e) => updateConsultationRow(pcon.id, 'treatmentResponse', e.target.value)}
                        className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs bg-white focus:outline-hidden focus:border-indigo-500"
                      >
                        <option value="IMPROVED">Improved</option>
                        <option value="UNCHANGED">Unchanged (No improvement)</option>
                        <option value="WORSENED">Worsened</option>
                        <option value="NOT_SURE">Not sure</option>
                      </select>
                    </div>

                    {/* Treatment Prescribed & Medicines Taken */}
                    <div className="sm:col-span-2">
                      <label className="block text-[10px] font-semibold text-slate-500 mb-1">
                        Medicines the Patient Reports Taking & Prescriptions
                      </label>
                      <input
                        type="text"
                        value={pcon.medicinesTaken}
                        onChange={(e) => updateConsultationRow(pcon.id, 'medicinesTaken', e.target.value)}
                        placeholder="e.g. Azithromycin 500mg, Paracetamol, Cough Syrup"
                        className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs bg-white focus:outline-hidden focus:border-indigo-500"
                      />
                    </div>

                    {/* Treatment Duration */}
                    <div>
                      <label className="block text-[10px] font-semibold text-slate-500 mb-1">
                        Duration of Treatment
                      </label>
                      <input
                        type="text"
                        value={pcon.durationOfTreatment}
                        onChange={(e) => updateConsultationRow(pcon.id, 'durationOfTreatment', e.target.value)}
                        placeholder="e.g. 5 days, 2 weeks"
                        className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs bg-white focus:outline-hidden focus:border-indigo-500"
                      />
                    </div>

                    {/* Previous Investigations */}
                    <div className="sm:col-span-2">
                      <label className="block text-[10px] font-semibold text-slate-500 mb-1">
                        Previous Investigations / Tests Done
                      </label>
                      <input
                        type="text"
                        value={pcon.previousInvestigations}
                        onChange={(e) => updateConsultationRow(pcon.id, 'previousInvestigations', e.target.value)}
                        placeholder="e.g. Chest X-Ray, CBC, Blood Sugar"
                        className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs bg-white focus:outline-hidden focus:border-indigo-500"
                      />
                    </div>

                    {/* Side effects reported */}
                    <div>
                      <label className="block text-[10px] font-semibold text-slate-500 mb-1">
                        Side Effects / Adverse Symptoms
                      </label>
                      <input
                        type="text"
                        value={pcon.sideEffects}
                        onChange={(e) => updateConsultationRow(pcon.id, 'sideEffects', e.target.value)}
                        placeholder="e.g. Nausea, skin rash"
                        className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs bg-white focus:outline-hidden focus:border-indigo-500"
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* SECTION 4: MEDICAL DOCUMENT UPLOAD (Prescriptions, Labs, EMR) */}
        <MedicalDocumentUpload
          patientCode={targetPatientId}
          canVerify={false}
          readOnly={false}
        />

        {/* SECTION 5: INTAKE VITAL SIGNS */}
        <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <HeartPulse className="w-4 h-4 text-blue-600" />
            <h3 className="text-sm font-bold text-slate-900">
              5. Intake Vital Signs (Station Measurements)
            </h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Temperature */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Body Temperature (°F)
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Thermometer className="w-4 h-4 text-amber-500" />
                </div>
                <input
                  type="number"
                  step="0.1"
                  value={temperature}
                  onChange={(e) => setTemperature(e.target.value)}
                  placeholder="e.g. 98.6"
                  className="w-full pl-9 pr-3 py-2 rounded-xl border border-slate-200 text-sm text-slate-800 focus:outline-hidden focus:border-blue-500 transition"
                />
              </div>
              {errors.temperature && (
                <p className="text-[11px] text-rose-500 mt-1">{errors.temperature}</p>
              )}
            </div>

            {/* Heart Rate */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Heart Rate (bpm)
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <HeartPulse className="w-4 h-4 text-rose-500" />
                </div>
                <input
                  type="number"
                  value={heartRate}
                  onChange={(e) => setHeartRate(e.target.value)}
                  placeholder="e.g. 78"
                  className="w-full pl-9 pr-3 py-2 rounded-xl border border-slate-200 text-sm text-slate-800 focus:outline-hidden focus:border-blue-500 transition"
                />
              </div>
              {errors.heartRate && (
                <p className="text-[11px] text-rose-500 mt-1">{errors.heartRate}</p>
              )}
            </div>

            {/* SpO2 */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Oxygen Saturation (SpO2 %)
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Wind className="w-4 h-4 text-blue-500" />
                </div>
                <input
                  type="number"
                  value={spo2}
                  onChange={(e) => setSpo2(e.target.value)}
                  placeholder="e.g. 98"
                  className="w-full pl-9 pr-3 py-2 rounded-xl border border-slate-200 text-sm text-slate-800 focus:outline-hidden focus:border-blue-500 transition"
                />
              </div>
              {errors.spo2 && (
                <p className="text-[11px] text-rose-500 mt-1">{errors.spo2}</p>
              )}
            </div>

            {/* Blood Pressure */}
            <div className="sm:col-span-2">
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Blood Pressure (mmHg)
              </label>
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="number"
                  value={systolicBP}
                  onChange={(e) => setSystolicBP(e.target.value)}
                  placeholder="Systolic (e.g. 120)"
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-sm text-slate-800 focus:outline-hidden focus:border-blue-500 transition"
                />
                <input
                  type="number"
                  value={diastolicBP}
                  onChange={(e) => setDiastolicBP(e.target.value)}
                  placeholder="Diastolic (e.g. 80)"
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-sm text-slate-800 focus:outline-hidden focus:border-blue-500 transition"
                />
              </div>
            </div>

            {/* Blood Sugar */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Random Blood Sugar (mg/dL)
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Droplet className="w-4 h-4 text-purple-500" />
                </div>
                <input
                  type="number"
                  value={sugarLevel}
                  onChange={(e) => setSugarLevel(e.target.value)}
                  placeholder="e.g. 110"
                  className="w-full pl-9 pr-3 py-2 rounded-xl border border-slate-200 text-sm text-slate-800 focus:outline-hidden focus:border-blue-500 transition"
                />
              </div>
            </div>
          </div>
        </div>

        {/* SECTION 6: CHRONIC COMORBIDITIES & MEDICAL HISTORY */}
        <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <History className="w-4 h-4 text-blue-600" />
            <h3 className="text-sm font-bold text-slate-900">
              6. Known Chronic Conditions & Past History
            </h3>
          </div>

          <div className="flex flex-wrap gap-2">
            {CHRONIC_CONDITIONS.map((cond) => {
              const isSelected = selectedDiseases.includes(cond);
              return (
                <button
                  key={cond}
                  type="button"
                  onClick={() => toggleDisease(cond)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-medium border transition cursor-pointer ${
                    isSelected
                      ? 'bg-indigo-50 border-indigo-400 text-indigo-700 font-bold'
                      : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  {cond}
                </button>
              );
            })}
          </div>

          <textarea
            value={customHistory}
            onChange={(e) => setCustomHistory(e.target.value)}
            rows="2"
            placeholder="Additional known chronic illnesses, previous hospitalizations, drug allergies..."
            className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-xs text-slate-800 focus:outline-hidden focus:border-blue-500 transition"
          />
        </div>

        {/* SUBMIT BUTTONS */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={handleReset}
            className="px-5 py-3 rounded-xl border border-slate-300 text-slate-700 text-sm font-semibold hover:bg-slate-100 transition cursor-pointer"
          >
            Clear
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            className="px-6 py-3 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm shadow-md shadow-blue-500/25 transition active:scale-95 cursor-pointer flex items-center gap-2"
          >
            <UserPlus className="w-4 h-4" />
            <span>Register & Prioritize Patient</span>
          </button>
        </div>
      </form>
    </div>
  );
}
