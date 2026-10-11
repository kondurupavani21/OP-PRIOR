import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { calculatePriority } from '../utils/priorityCalculator';
import { generateNextPatientId, findPatientByPhone, normalizePhone } from '../utils/patientUtils';
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
  History,
  Info,
  Phone,
  User,
  Calendar,
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

  // Symptoms
  const [selectedSymptoms, setSelectedSymptoms] = useState([]);
  const [customSymptom, setCustomSymptom] = useState('');

  // Vital Signs
  const [temperature, setTemperature] = useState('');
  const [heartRate, setHeartRate] = useState('');
  const [systolicBP, setSystolicBP] = useState('');
  const [diastolicBP, setDiastolicBP] = useState('');
  const [spo2, setSpo2] = useState('');
  const [sugarLevel, setSugarLevel] = useState('');

  // Medical History
  const [selectedDiseases, setSelectedDiseases] = useState([]);
  const [customHistory, setCustomHistory] = useState('');

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
        // Auto-fill previous details if not already changed
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

  const handleReset = () => {
    setPatientName('');
    setAge('');
    setGender('Male');
    setPhoneNumber('');
    setPatientType('New Card / First Visit');
    setExistingPatientMatch(null);
    setSelectedSymptoms([]);
    setCustomSymptom('');
    setTemperature('');
    setHeartRate('');
    setSystolicBP('');
    setDiastolicBP('');
    setSpo2('');
    setSugarLevel('');
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
    if (selectedSymptoms.length === 0) {
      err.symptoms = 'Please select or enter at least one presenting symptom.';
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

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!validate()) return;

    setIsSubmitting(true);

    // Format Blood Pressure string
    const bp = systolicBP && diastolicBP ? `${systolicBP}/${diastolicBP}` : systolicBP ? `${systolicBP}/80` : '120/80';

    // Generate or reuse dynamic Patient ID
    const assignedId = existingPatientMatch
      ? existingPatientMatch.patientId
      : generateNextPatientId(patients);

    // Prepare patient object
    const patientData = {
      patientId: assignedId,
      patientName: patientName.trim(),
      age: Number(age),
      gender,
      phoneNumber: phoneNumber.trim(),
      patientType: existingPatientMatch ? 'Existing Patient' : patientType,
      symptoms: selectedSymptoms,
      temperature: temperature ? Number(temperature) : 98.6,
      heartRate: heartRate ? Number(heartRate) : 75,
      bloodPressure: bp,
      spo2: spo2 ? Number(spo2) : 98,
      sugarLevel: sugarLevel ? Number(sugarLevel) : 100,
      previousDiseases: selectedDiseases,
      customHistory: customHistory.trim(),
      visits: existingPatientMatch ? existingPatientMatch.visits || [] : [],
    };

    // Calculate simulated AI priority
    const triageResult = calculatePriority(patientData);

    // Persist to storage & active queue
    registerPatientRecord(patientData, triageResult);

    setIsSubmitting(false);

    if (existingPatientMatch) {
      addToast(`Existing patient ${patientName} (${assignedId}) visit registered with Priority Score ${triageResult.priorityScore}!`, 'info');
    } else {
      addToast(`New patient ${patientName} registered as ${assignedId} with Priority Score ${triageResult.priorityScore}!`, 'success');
    }

    // Direct to AI Priority Assessment page to display rich score breakdown
    navigate(`/priority/${assignedId}`);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Page Title & Intro */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
            Patient Outpatient Registration
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Capture clinical intake vitals, detect existing records, and run the triage prioritization engine.
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
                Matched phone number to{' '}
                <strong>{existingPatientMatch.patientName}</strong> with{' '}
                {existingPatientMatch.visits?.length || 0} recorded previous visits.
                This new intake will be appended to their longitudinal history.
              </p>
            </div>
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
            {/* Phone Number (Primary Matching Key) */}
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
              <span className="text-[11px] text-slate-400 mt-1 block">
                Type a phone number to automatically look up past clinical records.
              </span>
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
                className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm text-slate-800 focus:outline-hidden focus:border-blue-500 focus:ring-3 focus:ring-blue-500/10 transition bg-white"
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

        {/* SECTION 2: CURRENT PRESENTING SYMPTOMS */}
        <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-blue-600" />
              <h3 className="text-sm font-bold text-slate-900">
                2. Current Symptoms *
              </h3>
            </div>
            <span className="text-xs text-slate-400">
              {selectedSymptoms.length} selected
            </span>
          </div>

          {errors.symptoms && (
            <p className="text-[11px] text-rose-500">{errors.symptoms}</p>
          )}

          {/* Symptom Quick Chips */}
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

        {/* SECTION 3: VITAL SIGNS */}
        <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <HeartPulse className="w-4 h-4 text-blue-600" />
            <h3 className="text-sm font-bold text-slate-900">
              3. Vital Signs (Heuristic Inputs)
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

            {/* Blood Pressure Systolic & Diastolic */}
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
              {errors.bloodPressure && (
                <p className="text-[11px] text-rose-500 mt-1">{errors.bloodPressure}</p>
              )}
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
              {errors.sugarLevel && (
                <p className="text-[11px] text-rose-500 mt-1">{errors.sugarLevel}</p>
              )}
            </div>
          </div>
        </div>

        {/* SECTION 4: MEDICAL HISTORY / PREVIOUS DISEASES */}
        <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <History className="w-4 h-4 text-blue-600" />
            <h3 className="text-sm font-bold text-slate-900">
              4. Previous Diseases / Medical History
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
            placeholder="Additional clinical notes, surgeries, drug allergies, or ongoing medications..."
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
