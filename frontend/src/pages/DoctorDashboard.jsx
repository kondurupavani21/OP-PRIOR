import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { useAuth } from '../context/AuthContext';
import { SeverityBadge, PriorityScoreBadge, PatientTypeBadge } from '../components/common/Badge';
import EmptyState from '../components/common/EmptyState';
import {
  Stethoscope,
  UserCheck,
  Clock,
  HeartPulse,
  Wind,
  Droplet,
  Thermometer,
  FileText,
  CheckCircle2,
  ArrowRight,
  AlertTriangle,
  History,
  Activity,
  Calendar,
} from 'lucide-react';
import { calculateWaitingTime } from '../utils/timeUtils';
import PreviousRecordsAndAISummaryPanel from '../components/medical/PreviousRecordsAndAISummaryPanel';

export default function DoctorDashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const {
    assignedDoctorPatient,
    currentPatient,
    sortedQueue,
    consultations,
    initiateCallPatient,
    patients,
  } = useApp();

  // If a patient was actively called and assigned, use that; otherwise fall back to top of queue for easy one-click call
  const activePatient = assignedDoctorPatient;

  // Longitudinal history for active patient if available
  const fullPatientRecord = activePatient
    ? patients.find((p) => p.patientId === activePatient.patientId)
    : null;

  const pastVisits = fullPatientRecord?.visits || [];
  const pastConsultations = pastVisits.filter((v) => v.status === 'Consulted');

  return (
    <div className="space-y-6">
      {/* Doctor Workspace Header */}
      <div className="bg-white rounded-3xl p-6 sm:p-7 border border-slate-200/80 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600 shadow-2xs shrink-0">
            <Stethoscope className="w-7 h-7" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight">
                {user?.name || 'Dr. Attending Physician'}
              </h2>
              <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 text-xs font-semibold border border-emerald-200">
                Online Desk
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Department: {user?.department || 'Outpatient Clinical Services'} • Attending Room 102
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to="/waiting-room"
            target="_blank"
            className="px-3.5 py-2.5 rounded-xl bg-cyan-50 border border-cyan-200 text-cyan-800 hover:bg-cyan-100 text-xs font-semibold flex items-center gap-1.5 transition shadow-2xs"
            title="Open OPD Waiting Room Public Display for patients"
          >
            <span>📺 Public Waiting Display</span>
          </Link>
          <Link
            to="/priority-queue"
            className="px-4 py-2.5 rounded-xl border border-slate-200 text-slate-700 hover:bg-slate-50 text-xs font-semibold transition"
          >
            Review Waiting Queue ({sortedQueue.length})
          </Link>
        </div>
      </div>

      {/* CURRENTLY ASSIGNED PATIENT SECTION */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Active Consultation Desk */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-3xl p-6 sm:p-7 border border-slate-200/80 shadow-xs">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100 mb-5">
              <div className="flex items-center gap-2">
                <UserCheck className="w-5 h-5 text-blue-600" />
                <h3 className="text-base font-bold text-slate-900">
                  Currently Assigned Patient
                </h3>
              </div>
              {activePatient && (
                <span className="text-xs font-mono font-bold bg-blue-50 text-blue-700 px-2.5 py-1 rounded-md border border-blue-100">
                  Room Ready
                </span>
              )}
            </div>

            {!activePatient ? (
              <div className="text-center py-10 px-4 bg-slate-50 rounded-2xl border border-dashed border-slate-200">
                <Stethoscope className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                <h4 className="text-base font-bold text-slate-700 mb-1">
                  No patient is currently assigned.
                </h4>
                <p className="text-xs text-slate-400 max-w-sm mx-auto mb-5">
                  Call the next patient from the waiting queue into the consultation room to begin clinical examination.
                </p>

                {currentPatient ? (
                  <button
                    onClick={() => initiateCallPatient(currentPatient)}
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-md shadow-blue-500/20 transition active:scale-95 cursor-pointer"
                  >
                    <UserCheck className="w-4 h-4" />
                    <span>Call Next Patient: {currentPatient.patientName} ({currentPatient.patientId})</span>
                  </button>
                ) : (
                  <Link
                    to="/patients/register"
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-slate-200 hover:bg-slate-300 text-slate-800 text-xs font-semibold transition"
                  >
                    Register New Patient
                  </Link>
                )}
              </div>
            ) : (
              <div className="space-y-6">
                {/* Active Patient Details Banner */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 rounded-2xl bg-blue-50/50 border border-blue-100">
                  <div>
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="font-mono text-xs font-bold bg-blue-200/80 text-blue-800 px-2 py-0.5 rounded">
                        {activePatient.patientId}
                      </span>
                      <PatientTypeBadge type={activePatient.patientType} />
                      <SeverityBadge severity={activePatient.severity} />
                    </div>
                    <h4 className="text-xl font-extrabold text-slate-900 tracking-tight">
                      {activePatient.patientName}
                    </h4>
                    <p className="text-xs text-slate-600 mt-1">
                      {activePatient.age} years old • {activePatient.gender || 'N/A'} • Contact: {activePatient.phoneNumber || 'N/A'}
                    </p>
                  </div>

                  <div className="text-right sm:border-l sm:border-blue-200 sm:pl-5">
                    <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">
                      Priority Score
                    </span>
                    <PriorityScoreBadge score={activePatient.priorityScore} />
                  </div>
                </div>

                {/* Presenting Symptoms & Vitals */}
                <div className="space-y-3">
                  <h5 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Clinical Intake Information
                  </h5>
                  <div className="p-4 rounded-xl bg-slate-50 border border-slate-100 space-y-3">
                    <div>
                      <span className="text-xs font-semibold text-slate-500">Reported Symptoms:</span>
                      <p className="text-sm font-bold text-slate-800 mt-0.5">
                        {Array.isArray(activePatient.symptoms)
                          ? activePatient.symptoms.join(', ')
                          : activePatient.symptoms || 'None specified'}
                      </p>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-200/60 text-xs">
                      <div>
                        <span className="text-slate-400 block text-[10px]">Pulse</span>
                        <strong className="text-slate-800">{activePatient.heartRate} bpm</strong>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px]">SpO2</span>
                        <strong className="text-slate-800">{activePatient.spo2}%</strong>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px]">Blood Pressure</span>
                        <strong className="text-slate-800">{activePatient.bloodPressure || '120/80'}</strong>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px]">Temperature</span>
                        <strong className="text-slate-800">{activePatient.temperature}°F</strong>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Recent Patient History */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h5 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                      Recent Medical History ({pastConsultations.length} previous visits)
                    </h5>
                    {pastConsultations.length > 0 && (
                      <Link
                        to={`/patients/${activePatient.patientId}/history`}
                        className="text-xs text-blue-600 hover:text-blue-700 font-semibold"
                      >
                        Full Record →
                      </Link>
                    )}
                  </div>

                  {pastConsultations.length === 0 ? (
                    <p className="text-xs text-slate-400 italic bg-slate-50 p-3 rounded-xl">
                      No previous consultation records on file for this patient.
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {pastConsultations.slice(0, 2).map((visit, i) => (
                        <div key={i} className="p-3 rounded-xl bg-slate-50 border border-slate-200/60 text-xs">
                          <div className="flex justify-between font-semibold text-slate-800 mb-1">
                            <span>Dx: {visit.diagnosis || 'Clinical visit'}</span>
                            <span className="text-slate-400">{visit.visitDate}</span>
                          </div>
                          {visit.doctorNotes && (
                            <p className="text-slate-500 line-clamp-1">{visit.doctorNotes}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Action CTA to open Consultation Form */}
                <div className="pt-3 border-t border-slate-100 flex items-center justify-end gap-3">
                  <button
                    onClick={() => initiateCallPatient(activePatient)}
                    className="px-4 py-2.5 rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-100 text-xs font-semibold cursor-pointer"
                  >
                    Recall / Check Presence
                  </button>

                  <Link
                    to={`/consultation/${activePatient.patientId}`}
                    className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-sm shadow-md shadow-emerald-600/20 transition active:scale-95 cursor-pointer"
                  >
                    <Stethoscope className="w-4 h-4" />
                    <span>Start Consultation</span>
                  </Link>
                </div>

                {/* Embedded Previous Medical Records & AI Clinical Summary Panel */}
                <div className="pt-2">
                  <PreviousRecordsAndAISummaryPanel
                    patientCode={activePatient.patientId}
                    encounterId={activePatient.encounterId || activePatient.encounter_id}
                    patientData={activePatient}
                    canVerify={true}
                  />
                </div>
              </div>
            )}
          </div>
        </div>


        {/* Right 1 Col: Upcoming Patients in Queue Peek */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-white rounded-3xl p-6 border border-slate-200/80 shadow-xs">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h4 className="text-sm font-bold text-slate-900">
                  Waiting Queue Peek
                </h4>
                <p className="text-xs text-slate-400">Next patients in line</p>
              </div>
              <span className="text-xs font-mono font-bold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700">
                {sortedQueue.length} Waiting
              </span>
            </div>

            {sortedQueue.length === 0 ? (
              <p className="text-xs text-center text-slate-400 py-8">
                No patients currently waiting.
              </p>
            ) : (
              <div className="space-y-2.5">
                {sortedQueue.slice(0, 4).map((p, i) => (
                  <div
                    key={p.patientId}
                    className="p-3 rounded-xl bg-slate-50 hover:bg-blue-50/50 border border-slate-100 transition flex items-center justify-between gap-2 text-xs"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono text-[10px] text-slate-400 font-bold">
                          #{i + 1}
                        </span>
                        <strong className="text-slate-800 truncate block">
                          {p.patientName}
                        </strong>
                      </div>
                      <div className="text-[11px] text-slate-400 flex items-center gap-2 mt-0.5">
                        <span>{p.patientId}</span>
                        <span>•</span>
                        <span>{calculateWaitingTime(p.queueEntryTime)}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      <SeverityBadge severity={p.severity} size="sm" />
                      <button
                        onClick={() => initiateCallPatient(p)}
                        className="px-2.5 py-1 rounded-lg bg-blue-600 text-white font-semibold text-[11px] hover:bg-blue-700 transition cursor-pointer"
                      >
                        Call
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="mt-4 pt-3 border-t border-slate-100 text-center">
              <Link
                to="/priority-queue"
                className="text-xs font-semibold text-blue-600 hover:text-blue-700"
              >
                View Full Queue →
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
