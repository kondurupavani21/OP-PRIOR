import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { SeverityBadge, PriorityScoreBadge, PatientTypeBadge } from '../components/common/Badge';
import EmptyState from '../components/common/EmptyState';
import {
  User,
  Phone,
  Calendar,
  HeartPulse,
  Wind,
  Droplet,
  Thermometer,
  Activity,
  History,
  FileText,
  Stethoscope,
  Sparkles,
  ArrowRight,
  ChevronRight,
} from 'lucide-react';

export default function PatientDetails() {
  const { id } = useParams();
  const { patients, queue, initiateCallPatient } = useApp();

  const patientInQueue = queue.find((q) => q.patientId === id);
  const patient = patients.find((p) => p.patientId === id) || patientInQueue;

  if (!patient) {
    return (
      <EmptyState
        title="Patient Record Not Found"
        description={`No registered record matching ID "${id}" was found in stored patient data.`}
        actionText="Back to Patients"
        actionLink="/priority-queue"
      />
    );
  }

  const visits = patient.visits || [];

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Patient Profile Card */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200/80 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-100">
          <div className="flex items-start gap-4">
            <div className="w-16 h-16 rounded-2xl bg-blue-50 border border-blue-100 text-blue-600 flex items-center justify-center font-bold text-xl shrink-0">
              {patient.patientName?.charAt(0) || 'P'}
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="font-mono text-xs font-bold bg-blue-100/70 text-blue-700 px-2 py-0.5 rounded">
                  {patient.patientId}
                </span>
                <PatientTypeBadge type={patient.patientType} />
                <SeverityBadge severity={patient.currentSeverity || patient.severity} />
              </div>
              <h2 className="text-2xl font-black text-slate-900 tracking-tight">
                {patient.patientName}
              </h2>
              <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 mt-1">
                <span>{patient.age} years old</span>
                <span>•</span>
                <span>{patient.gender || 'Not specified'}</span>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <Phone className="w-3.5 h-3.5 text-slate-400" />
                  {patient.phoneNumber}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-auto">
            <Link
              to={`/priority/${patient.patientId}`}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-blue-50 text-blue-700 hover:bg-blue-100 text-xs font-semibold transition"
            >
              <Sparkles className="w-4 h-4" />
              <span>AI Triage Details</span>
            </Link>
            {patientInQueue && (
              <button
                onClick={() => initiateCallPatient(patientInQueue)}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-blue-600 text-white hover:bg-blue-700 text-xs font-semibold shadow-xs shadow-blue-500/20 transition cursor-pointer"
              >
                <Stethoscope className="w-4 h-4" />
                <span>Call Patient</span>
              </button>
            )}
          </div>
        </div>

        {/* Vital Signs Grid */}
        <div className="pt-6 space-y-3">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Current Vital Signs
          </h4>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-xs">
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-slate-400 text-[10px] uppercase font-semibold">Pulse Rate</span>
              <div className="flex items-center gap-1 font-bold text-slate-800 mt-1">
                <HeartPulse className="w-3.5 h-3.5 text-rose-500" />
                <span>{patient.heartRate} bpm</span>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-slate-400 text-[10px] uppercase font-semibold">SpO2 Oxygen</span>
              <div className="flex items-center gap-1 font-bold text-slate-800 mt-1">
                <Wind className="w-3.5 h-3.5 text-blue-500" />
                <span>{patient.spo2}%</span>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-slate-400 text-[10px] uppercase font-semibold">Blood Pressure</span>
              <div className="font-bold text-slate-800 mt-1">
                {patient.bloodPressure || '120/80'}
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-slate-400 text-[10px] uppercase font-semibold">Temperature</span>
              <div className="flex items-center gap-1 font-bold text-slate-800 mt-1">
                <Thermometer className="w-3.5 h-3.5 text-amber-500" />
                <span>{patient.temperature}°F</span>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-slate-400 text-[10px] uppercase font-semibold">Blood Sugar</span>
              <div className="flex items-center gap-1 font-bold text-slate-800 mt-1">
                <Droplet className="w-3.5 h-3.5 text-purple-500" />
                <span>{patient.sugarLevel} mg/dL</span>
              </div>
            </div>
          </div>
        </div>

        {/* Symptoms & Chronic Disease History */}
        <div className="pt-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-100 space-y-1.5">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 block">
              Presenting Symptoms
            </span>
            <p className="text-sm font-semibold text-slate-800">
              {Array.isArray(patient.symptoms)
                ? patient.symptoms.join(', ')
                : patient.symptoms || 'None recorded'}
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-100 space-y-1.5">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 block">
              Previous Diseases / Medical History
            </span>
            <p className="text-sm font-semibold text-slate-800">
              {Array.isArray(patient.previousDiseases) && patient.previousDiseases.length > 0
                ? patient.previousDiseases.join(', ')
                : 'No chronic diseases reported'}
            </p>
            {patient.customHistory && (
              <p className="text-xs text-slate-500 mt-1">{patient.customHistory}</p>
            )}
          </div>
        </div>
      </div>

      {/* VISIT & CONSULTATION HISTORY */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200/80 shadow-xs space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <History className="w-5 h-5 text-blue-600" />
            <h3 className="text-base font-bold text-slate-900">
              Longitudinal Visit History ({visits.length} recorded)
            </h3>
          </div>
          <Link
            to={`/patients/${patient.patientId}/history`}
            className="text-xs text-blue-600 hover:text-blue-700 font-semibold"
          >
            Full Timeline View →
          </Link>
        </div>

        {visits.length === 0 ? (
          <p className="text-xs text-slate-400 italic py-4">
            No previous records available for this patient.
          </p>
        ) : (
          <div className="space-y-3">
            {visits.map((v, i) => (
              <div
                key={v.visitId || i}
                className="p-4 rounded-2xl bg-slate-50 border border-slate-200/70 space-y-2 text-xs"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-800 text-sm">
                      Visit #{visits.length - i}
                    </span>
                    <span className="text-slate-400">
                      {v.visitDate} at {v.visitTime || ''}
                    </span>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded-full font-semibold text-[10px] ${
                      v.status === 'Consulted'
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-amber-100 text-amber-800'
                    }`}
                  >
                    {v.status || 'Waiting'}
                  </span>
                </div>

                <p className="text-slate-600">
                  <strong>Symptoms:</strong>{' '}
                  {Array.isArray(v.symptoms) ? v.symptoms.join(', ') : v.symptoms}
                </p>

                {v.diagnosis && (
                  <p className="text-blue-900 bg-blue-50 p-2.5 rounded-xl border border-blue-100 font-medium">
                    <strong>Diagnosis:</strong> {v.diagnosis}
                  </p>
                )}

                {v.doctorNotes && (
                  <p className="text-slate-500 italic">
                    Notes: {v.doctorNotes}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
