import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { useAuth } from '../context/AuthContext';
import { SeverityBadge, PriorityScoreBadge, PatientTypeBadge } from '../components/common/Badge';
import EmptyState from '../components/common/EmptyState';
import {
  Stethoscope,
  ClipboardCheck,
  Plus,
  Trash2,
  Calendar,
  FileText,
  Pill,
  HeartPulse,
  Wind,
  Droplet,
  Thermometer,
  AlertCircle,
  Save,
  CheckCircle2,
  ArrowRight,
  Sparkles,
} from 'lucide-react';
import api from '../services/api';
import PreviousRecordsAndAISummaryPanel from '../components/medical/PreviousRecordsAndAISummaryPanel';

const COMMON_DIAGNOSES = [
  'Acute Viral Upper Respiratory Infection',
  'Acute Bronchitis',
  'Acute Gastroenteritis',
  'Hypertensive Urgency / Uncontrolled HTN',
  'Type 2 Diabetes Mellitus - Follow-up',
  'Migraine / Tension Cephalea',
  'Musculoskeletal Strain / Back Pain',
  'Allergic Rhinitis / Dermatitis',
  'General Fatigue & Nutritional Evaluation',
];

export default function Consultation() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const {
    patients,
    queue,
    assignedDoctorPatient,
    completeConsultation,
    addToast,
  } = useApp();

  // Resolve target patient: by url param, or assigned patient, or top of queue
  const targetId = id || assignedDoctorPatient?.patientId || (queue.length > 0 ? queue[0].patientId : null);

  const patientInQueue = queue.find((q) => q.patientId === targetId);
  const patient = patients.find((p) => p.patientId === targetId) || patientInQueue;

  // Consultation Form State
  const [diagnosis, setDiagnosis] = useState('');
  const [doctorNotes, setDoctorNotes] = useState('');
  const [followUpDate, setFollowUpDate] = useState('');
  const [prescriptions, setPrescriptions] = useState([
    {
      medicine: 'Paracetamol 650mg',
      dosage: '1 tab',
      frequency: 'TDS (3 times/day)',
      duration: '3 days',
      instructions: 'After meals',
    },
  ]);

  // Validation
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);



  if (!patient) {
    return (
      <EmptyState
        icon={Stethoscope}
        title="No Patient Selected for Consultation"
        description="Select an active waiting patient from the Priority Queue or Doctor Dashboard to begin."
        actionText="View Waiting Queue"
        actionLink="/priority-queue"
      />
    );
  }

  const addPrescriptionRow = () => {
    setPrescriptions((prev) => [
      ...prev,
      {
        medicine: '',
        dosage: '',
        frequency: 'Once daily',
        duration: '5 days',
        instructions: 'After food',
      },
    ]);
  };

  const updatePrescriptionRow = (index, field, value) => {
    setPrescriptions((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      return updated;
    });
  };

  const removePrescriptionRow = (index) => {
    setPrescriptions((prev) => prev.filter((_, i) => i !== index));
  };

  const handleComplete = (e) => {
    e.preventDefault();
    setError('');

    if (!diagnosis.trim()) {
      setError('Please provide a clinical diagnosis before completing the consultation.');
      return;
    }

    setIsSubmitting(true);

    const consultationData = {
      patientId: patient.patientId,
      patientName: patient.patientName,
      doctorName: user?.name || 'Dr. Attending Physician',
      diagnosis: diagnosis.trim(),
      prescription: prescriptions.filter((p) => p.medicine && p.medicine.trim()),
      doctorNotes: doctorNotes.trim(),
      followUpDate,
      vitalsSummary: {
        heartRate: patient.heartRate,
        spo2: patient.spo2,
        bloodPressure: patient.bloodPressure,
        temperature: patient.temperature,
      },
    };

    completeConsultation(consultationData);
    setIsSubmitting(false);

    // Section 25 & 27: Navigate back to updated queue
    navigate('/priority-queue');
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Consultation Header Banner */}
      <div className="bg-white rounded-3xl p-6 sm:p-7 border border-slate-200/80 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-slate-100">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="font-mono text-xs font-bold bg-blue-100/70 text-blue-700 px-2.5 py-0.5 rounded-md">
                {patient.patientId}
              </span>
              <PatientTypeBadge type={patient.patientType} />
              <SeverityBadge severity={patient.severity} />
            </div>
            <h2 className="text-2xl font-black text-slate-900 tracking-tight">
              {patient.patientName}
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              {patient.age} yrs • {patient.gender || 'N/A'} • Attending Doctor: <strong>{user?.name || 'Dr. Attending Physician'}</strong>
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Link
              to={`/patients/${patient.patientId}/history`}
              className="px-3 py-2 rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-50 text-xs font-semibold transition"
            >
              Past Visit History
            </Link>
          </div>
        </div>

        {/* Presenting Symptoms & Vitals Snapshot */}
        <div className="pt-4 grid grid-cols-2 sm:grid-cols-5 gap-3 text-xs">
          <div className="bg-slate-50 rounded-xl p-2.5 border border-slate-100">
            <span className="text-slate-400 block text-[10px] uppercase font-semibold">Pulse</span>
            <div className="flex items-center gap-1 font-bold text-slate-800 mt-0.5">
              <HeartPulse className="w-3.5 h-3.5 text-rose-500" />
              <span>{patient.heartRate} bpm</span>
            </div>
          </div>
          <div className="bg-slate-50 rounded-xl p-2.5 border border-slate-100">
            <span className="text-slate-400 block text-[10px] uppercase font-semibold">SpO2</span>
            <div className="flex items-center gap-1 font-bold text-slate-800 mt-0.5">
              <Wind className="w-3.5 h-3.5 text-blue-500" />
              <span>{patient.spo2}%</span>
            </div>
          </div>
          <div className="bg-slate-50 rounded-xl p-2.5 border border-slate-100">
            <span className="text-slate-400 block text-[10px] uppercase font-semibold">Blood Pressure</span>
            <div className="font-bold text-slate-800 mt-0.5">
              {patient.bloodPressure || '120/80'}
            </div>
          </div>
          <div className="bg-slate-50 rounded-xl p-2.5 border border-slate-100">
            <span className="text-slate-400 block text-[10px] uppercase font-semibold">Temperature</span>
            <div className="flex items-center gap-1 font-bold text-slate-800 mt-0.5">
              <Thermometer className="w-3.5 h-3.5 text-amber-500" />
              <span>{patient.temperature}°F</span>
            </div>
          </div>
          <div className="bg-slate-50 rounded-xl p-2.5 border border-slate-100">
            <span className="text-slate-400 block text-[10px] uppercase font-semibold">Priority</span>
            <div className="mt-0.5">
              <PriorityScoreBadge score={patient.priorityScore} />
            </div>
          </div>
        </div>

        {patient.symptoms && (
          <div className="mt-3 p-3 rounded-xl bg-blue-50/50 border border-blue-100 text-xs">
            <span className="font-semibold text-blue-900">Chief Complaints:</span>{' '}
            <span className="text-blue-800">
              {Array.isArray(patient.symptoms) ? patient.symptoms.join(', ') : patient.symptoms}
            </span>
          </div>
        )}
      </div>

      {/* CONSULTATION CLINICAL FORM */}
      <form onSubmit={handleComplete} className="space-y-6">
        {error && (
          <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 flex items-center gap-2 text-rose-700 text-xs font-medium">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
            <span>{error}</span>
          </div>
        )}

        {/* PREVIOUS MEDICAL RECORDS & AI CLINICAL SUMMARY (5-SECTION CLINICAL GOVERNANCE) */}
        <PreviousRecordsAndAISummaryPanel
          patientCode={patient.patientId}
          encounterId={patient.encounter_id || patient.encounterId || patient.id || targetId}
          patientData={patient}
          canVerify={true}
          onUseDiagnosis={(diag) => setDiagnosis(diag)}
        />

        {/* 1. Clinical Diagnosis */}
        <div className="bg-white rounded-3xl p-6 border border-slate-200/80 shadow-xs space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <FileText className="w-4 h-4 text-blue-600" />
            <h3 className="text-sm font-bold text-slate-900">
              1. Clinical Diagnosis *
            </h3>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Primary Medical Diagnosis
            </label>
            <input
              type="text"
              value={diagnosis}
              onChange={(e) => setDiagnosis(e.target.value)}
              placeholder="e.g. Acute Upper Respiratory Tract Infection with reactive bronchospasm"
              className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm text-slate-800 focus:outline-hidden focus:border-blue-500 focus:ring-3 focus:ring-blue-500/10 transition font-medium"
            />
          </div>

          {/* Quick Clinical Suggestions Chips */}
          <div>
            <span className="block text-[11px] font-semibold text-slate-400 mb-2">
              Common Clinical Suggestions:
            </span>
            <div className="flex flex-wrap gap-1.5">
              {COMMON_DIAGNOSES.map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setDiagnosis(d)}
                  className="px-2.5 py-1 rounded-lg bg-slate-50 hover:bg-blue-50 hover:border-blue-300 border border-slate-200 text-[11px] font-medium text-slate-600 transition cursor-pointer"
                >
                  + {d}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* 2. Prescription Table */}
        <div className="bg-white rounded-3xl p-6 border border-slate-200/80 shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <Pill className="w-4 h-4 text-blue-600" />
              <h3 className="text-sm font-bold text-slate-900">
                2. Medical Prescription & Regimen
              </h3>
            </div>
            <button
              type="button"
              onClick={addPrescriptionRow}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-blue-50 text-blue-600 hover:bg-blue-100 text-xs font-semibold transition cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Medication</span>
            </button>
          </div>

          <div className="space-y-3">
            {prescriptions.map((rx, idx) => (
              <div
                key={idx}
                className="grid grid-cols-1 sm:grid-cols-12 gap-2.5 p-3 rounded-2xl bg-slate-50 border border-slate-200/70 items-center text-xs"
              >
                {/* Medicine Name */}
                <div className="sm:col-span-4">
                  <label className="block text-[10px] font-semibold text-slate-400 mb-1">
                    Medicine / Drug Name
                  </label>
                  <input
                    type="text"
                    value={rx.medicine}
                    onChange={(e) => updatePrescriptionRow(idx, 'medicine', e.target.value)}
                    placeholder="e.g. Amoxicillin 500mg"
                    className="w-full px-3 py-1.5 rounded-lg border border-slate-200 text-xs bg-white focus:outline-hidden focus:border-blue-500"
                  />
                </div>

                {/* Dosage */}
                <div className="sm:col-span-2">
                  <label className="block text-[10px] font-semibold text-slate-400 mb-1">
                    Dosage
                  </label>
                  <input
                    type="text"
                    value={rx.dosage}
                    onChange={(e) => updatePrescriptionRow(idx, 'dosage', e.target.value)}
                    placeholder="1 tab"
                    className="w-full px-3 py-1.5 rounded-lg border border-slate-200 text-xs bg-white focus:outline-hidden focus:border-blue-500"
                  />
                </div>

                {/* Frequency */}
                <div className="sm:col-span-2">
                  <label className="block text-[10px] font-semibold text-slate-400 mb-1">
                    Frequency
                  </label>
                  <select
                    value={rx.frequency}
                    onChange={(e) => updatePrescriptionRow(idx, 'frequency', e.target.value)}
                    className="w-full px-2 py-1.5 rounded-lg border border-slate-200 text-xs bg-white focus:outline-hidden focus:border-blue-500"
                  >
                    <option value="Once daily">Once daily</option>
                    <option value="BD (Twice daily)">BD (Twice daily)</option>
                    <option value="TDS (3 times/day)">TDS (3 times/day)</option>
                    <option value="QID (4 times/day)">QID (4 times/day)</option>
                    <option value="SOS (As needed)">SOS (As needed)</option>
                  </select>
                </div>

                {/* Duration */}
                <div className="sm:col-span-2">
                  <label className="block text-[10px] font-semibold text-slate-400 mb-1">
                    Duration
                  </label>
                  <input
                    type="text"
                    value={rx.duration}
                    onChange={(e) => updatePrescriptionRow(idx, 'duration', e.target.value)}
                    placeholder="5 days"
                    className="w-full px-3 py-1.5 rounded-lg border border-slate-200 text-xs bg-white focus:outline-hidden focus:border-blue-500"
                  />
                </div>

                {/* Delete button */}
                <div className="sm:col-span-2 flex justify-end pt-3 sm:pt-0">
                  <button
                    type="button"
                    onClick={() => removePrescriptionRow(idx)}
                    className="p-2 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition cursor-pointer"
                    title="Remove medication"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 3. Clinical Notes & Follow-up */}
        <div className="bg-white rounded-3xl p-6 border border-slate-200/80 shadow-xs space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <Calendar className="w-4 h-4 text-blue-600" />
            <h3 className="text-sm font-bold text-slate-900">
              3. Doctor Advice & Follow-up
            </h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="sm:col-span-2">
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Physician Notes / Advice to Patient
              </label>
              <textarea
                value={doctorNotes}
                onChange={(e) => setDoctorNotes(e.target.value)}
                rows="3"
                placeholder="Maintain adequate oral hydration, rest for 48 hours. Report to ER immediately if dyspnea worsens..."
                className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-xs text-slate-800 focus:outline-hidden focus:border-blue-500 transition"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Follow-up Date
              </label>
              <input
                type="date"
                value={followUpDate}
                onChange={(e) => setFollowUpDate(e.target.value)}
                className="w-full px-3 py-2.5 rounded-xl border border-slate-200 text-xs text-slate-800 focus:outline-hidden focus:border-blue-500 transition bg-white"
              />
              <span className="text-[11px] text-slate-400 mt-1 block">
                Scheduled return date for review.
              </span>
            </div>
          </div>
        </div>

        {/* SUBMISSION BUTTONS */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <Link
            to="/priority-queue"
            className="px-5 py-3 rounded-xl border border-slate-300 text-slate-700 text-sm font-semibold hover:bg-slate-100 transition cursor-pointer"
          >
            Cancel
          </Link>

          <button
            type="submit"
            disabled={isSubmitting}
            className="px-6 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-sm shadow-md shadow-emerald-500/20 transition active:scale-95 cursor-pointer flex items-center gap-2"
          >
            <ClipboardCheck className="w-5 h-5" />
            <span>Complete Consultation & Update Queue</span>
          </button>
        </div>
      </form>
    </div>
  );
}
