import React from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { SeverityBadge, EmergencyRiskBadge, PatientTypeBadge } from '../components/common/Badge';
import EmptyState from '../components/common/EmptyState';
import {
  Sparkles,
  ShieldAlert,
  ArrowRight,
  ListOrdered,
  Stethoscope,
  Clock,
  HeartPulse,
  Thermometer,
  Wind,
  Droplet,
  Info,
  CheckCircle2,
  AlertTriangle,
  History,
} from 'lucide-react';

export default function PriorityAssessment() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { patients, queue, initiateCallPatient } = useApp();

  // Find patient from active queue or patients store
  const queueItem = queue.find((q) => q.patientId === id);
  const patient = patients.find((p) => p.patientId === id) || queueItem;

  if (!patient) {
    return (
      <EmptyState
        title="Patient Record Not Found"
        description={`No registered record matching Patient ID "${id}" was found in LocalStorage.`}
        actionText="Return to Priority Queue"
        actionLink="/priority-queue"
      />
    );
  }

  // Get current visit details
  const currentVisit = patient.visits && patient.visits.length > 0
    ? patient.visits[patient.visits.length - 1]
    : patient;

  const score = currentVisit.priorityScore || patient.priorityScore || 20;
  const severity = currentVisit.severity || patient.severity || 'LOW';
  const emergencyRisk = currentVisit.emergencyRisk || patient.emergencyRisk || 'NO';
  const factors = currentVisit.factors || [];

  // Determine color scheme based on score or critical severity
  const isHigh = score >= 80 || severity === 'CRITICAL' || severity === 'HIGH';
  const isMed = !isHigh && score >= 50;

  const scoreColor = isHigh
    ? 'text-rose-600 bg-rose-50 border-rose-200'
    : isMed
    ? 'text-amber-600 bg-amber-50 border-amber-200'
    : 'text-emerald-600 bg-emerald-50 border-emerald-200';

  const isCriticalHypoxia = patient.spo2 && Number(patient.spo2) < 90;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Disclaimer Alert */}
      <div className="p-3.5 rounded-2xl bg-blue-50/80 border border-blue-200 flex items-center gap-3 text-xs text-blue-900">
        <Info className="w-5 h-5 text-blue-600 shrink-0" />
        <p>
          <strong className="font-semibold">Simulated Priority Assessment:</strong>{' '}
          This score is computed using the frontend heuristic rule engine for demonstration. It is a preliminary decision-support indicator and requires qualified clinician evaluation.
        </p>
      </div>

      {/* Critical Hypoxia Alert Banner */}
      {isCriticalHypoxia && (
        <div className="p-4 rounded-2xl bg-rose-50 border-2 border-rose-300 flex items-start gap-3 text-rose-950 shadow-xs">
          <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div>
            <p className="text-xs font-bold text-rose-900">
              Critical Hypoxia Alert (SpO2 {patient.spo2}%): Immediate Medical Escalation Required
            </p>
            <p className="text-[11px] text-rose-800 mt-1">
              Pulse oximetry &lt;90% indicates profound respiratory risk. Verify sensor placement, probe contact, and pulse waveform artifact immediately without delaying resuscitation, oxygen therapy, or emergency clinician evaluation.
            </p>
            <p className="text-[10px] text-rose-700/80 mt-1 italic">
              * Clinical decision-support advisory only. All triage recommendations must be confirmed by qualified medical staff.
            </p>
          </div>
        </div>
      )}

      {/* PATIENT HEADER SUMMARY CARD */}
      <div className="bg-white rounded-3xl p-6 sm:p-7 border border-slate-200/80 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-100">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-xs font-mono font-bold bg-blue-100/70 text-blue-700 px-2.5 py-0.5 rounded-md">
                {patient.patientId}
              </span>
              <PatientTypeBadge type={patient.patientType} />
              <SeverityBadge severity={severity} />
            </div>
            <h2 className="text-2xl font-black text-slate-900 tracking-tight">
              {patient.patientName}
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              {patient.age} years old • {patient.gender || 'N/A'} • Contact: {patient.phoneNumber || 'N/A'}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Link
              to={`/patients/${patient.patientId}/history`}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-slate-200 text-slate-700 hover:bg-slate-50 text-xs font-semibold transition"
            >
              <History className="w-4 h-4 text-slate-500" />
              <span>Medical History</span>
            </Link>
          </div>
        </div>

        {/* Presenting Vitals Quick Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 pt-5 text-xs">
          <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
            <span className="text-slate-400 block text-[10px] uppercase font-semibold">Pulse Rate</span>
            <div className="flex items-center gap-1.5 font-bold text-slate-800 mt-1">
              <HeartPulse className="w-3.5 h-3.5 text-rose-500" />
              <span>{patient.heartRate} bpm</span>
            </div>
          </div>

          <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
            <span className="text-slate-400 block text-[10px] uppercase font-semibold">Oxygen (SpO2)</span>
            <div className="flex items-center gap-1.5 font-bold text-slate-800 mt-1">
              <Wind className="w-3.5 h-3.5 text-blue-500" />
              <span>{patient.spo2}%</span>
            </div>
          </div>

          <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
            <span className="text-slate-400 block text-[10px] uppercase font-semibold">Blood Pressure</span>
            <div className="font-bold text-slate-800 mt-1">
              {patient.bloodPressure || '120/80'}
            </div>
          </div>

          <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
            <span className="text-slate-400 block text-[10px] uppercase font-semibold">Temperature</span>
            <div className="flex items-center gap-1.5 font-bold text-slate-800 mt-1">
              <Thermometer className="w-3.5 h-3.5 text-amber-500" />
              <span>{patient.temperature}°F</span>
            </div>
          </div>

          <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
            <span className="text-slate-400 block text-[10px] uppercase font-semibold">Blood Sugar</span>
            <div className="flex items-center gap-1.5 font-bold text-slate-800 mt-1">
              <Droplet className="w-3.5 h-3.5 text-purple-500" />
              <span>{patient.sugarLevel} mg/dL</span>
            </div>
          </div>
        </div>
      </div>

      {/* AI TRIAGE CALCULATION RESULTS PANEL */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200/80 shadow-xs space-y-6">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-blue-600" />
          <h3 className="text-lg font-bold text-slate-900">
            AI Heuristic Triage Score
          </h3>
        </div>

        {/* 3 Metric Summary Pillars */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Pillar 1: Final Priority Score */}
          <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200/70 text-center flex flex-col items-center justify-center">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-1">
              Final Priority Score
            </span>
            <div className={`text-4xl sm:text-5xl font-extrabold font-mono px-4 py-1.5 rounded-2xl border ${scoreColor} my-2`}>
              {score}
              <span className="text-xl font-normal text-slate-400">/100</span>
            </div>
            <p className="text-[11px] text-slate-500">
              Severity Score: <strong>{score}</strong>
            </p>
          </div>

          {/* Pillar 2: Priority Classification */}
          <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200/70 text-center flex flex-col items-center justify-center">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-1">
              Priority Classification
            </span>
            <div className="my-3">
              <SeverityBadge severity={severity} size="lg" />
            </div>
            <span className="text-xs font-medium text-slate-600">
              {severity === 'CRITICAL'
                ? 'Immediate life-safety resuscitation & clinical evaluation'
                : severity === 'HIGH'
                ? 'Immediate clinical attention recommended'
                : severity === 'MEDIUM'
                ? 'Moderate outpatient urgency'
                : 'Routine outpatient checkup'}
            </span>
          </div>

          {/* Pillar 3: Emergency Risk Assessment */}
          <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200/70 text-center flex flex-col items-center justify-center">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-1">
              Emergency Risk Flag
            </span>
            <div className="my-3">
              <EmergencyRiskBadge emergencyRisk={emergencyRisk} />
            </div>
            <span className="text-xs text-slate-500">
              {emergencyRisk === 'YES'
                ? 'Patient exhibits red-flag physiological indicators'
                : 'No acute emergency signs triggered'}
            </span>
          </div>
        </div>

        {/* ITEMIZED CONTRIBUTING FACTORS BREAKDOWN */}
        <div className="space-y-3 pt-3">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Contributing Heuristic Factors & Reasoning
          </h4>

          <div className="space-y-2">
            {factors.length === 0 ? (
              <p className="text-xs text-slate-500 italic">
                Baseline stable parameters. No abnormal physiological deviations recorded.
              </p>
            ) : (
              factors.map((f, i) => {
                let badgeStyle = 'bg-blue-50 border-blue-200 text-blue-700';
                let icon = <Info className="w-4 h-4 text-blue-500" />;

                if (f.level === 'critical') {
                  badgeStyle = 'bg-rose-50 border-rose-200 text-rose-800';
                  icon = <AlertTriangle className="w-4 h-4 text-rose-600" />;
                } else if (f.level === 'warning') {
                  badgeStyle = 'bg-amber-50 border-amber-200 text-amber-800';
                  icon = <AlertTriangle className="w-4 h-4 text-amber-600" />;
                }

                return (
                  <div
                    key={i}
                    className={`p-3 rounded-xl border flex items-center justify-between gap-3 ${badgeStyle}`}
                  >
                    <div className="flex items-center gap-3">
                      {icon}
                      <div>
                        <p className="text-xs font-bold">{f.title}</p>
                        <p className="text-[11px] opacity-90">{f.description}</p>
                      </div>
                    </div>
                    <span className="font-mono text-xs font-bold px-2 py-0.5 rounded-md bg-white/60">
                      {f.points}
                    </span>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* ACTION BUTTONS */}
        <div className="pt-4 border-t border-slate-100 flex flex-wrap items-center justify-end gap-3">
          <Link
            to="/priority-queue"
            className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm shadow-md shadow-blue-500/20 transition active:scale-95 cursor-pointer"
          >
            <ListOrdered className="w-4 h-4" />
            <span>Proceed to Priority Queue</span>
          </Link>

          {queueItem && (
            <button
              onClick={() => initiateCallPatient(queueItem)}
              className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-sm shadow-md shadow-emerald-500/20 transition active:scale-95 cursor-pointer"
            >
              <Stethoscope className="w-4 h-4" />
              <span>Call for Consultation</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
