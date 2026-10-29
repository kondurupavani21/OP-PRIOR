import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { SeverityBadge, PriorityScoreBadge, PatientTypeBadge } from '../components/common/Badge';
import EmptyState from '../components/common/EmptyState';
import {
  History,
  Calendar,
  Search,
  User,
  Phone,
  FileText,
  Stethoscope,
  Pill,
  Clock,
  ArrowRight,
  Sparkles,
} from 'lucide-react';

export default function PatientHistory() {
  const { id } = useParams();
  const { patients, queue } = useApp();

  const [search, setSearch] = useState('');
  const [selectedPatientId, setSelectedPatientId] = useState(id || null);

  // If URL has ID, sync selectedPatientId
  React.useEffect(() => {
    if (id) {
      setSelectedPatientId(id);
    } else if (!selectedPatientId && patients.length > 0) {
      setSelectedPatientId(patients[0].patientId);
    }
  }, [id, patients]);

  // Filtered patients list for left sidebar selector
  const filteredPatients = patients.filter((p) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase().trim();
    const name = String(p.patientName || '').toLowerCase();
    const pid = String(p.patientId || '').toLowerCase();
    const phone = String(p.phoneNumber || '').toLowerCase();
    return name.includes(q) || pid.includes(q) || phone.includes(q);
  });

  const selectedPatient = patients.find((p) => p.patientId === selectedPatientId);
  const visits = selectedPatient?.visits || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
            Patient Longitudinal History
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Complete archival record of previous hospital visits, clinical diagnoses, and prescriptions.
          </p>
        </div>

        <Link
          to="/patients/register"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-xs shadow-blue-500/20 transition self-start"
        >
          Register New Visit
        </Link>
      </div>

      {patients.length === 0 ? (
        <EmptyState
          icon={History}
          title="No previous records available."
          description="There are no registered patients in the system yet. Once patients are registered and triaged, their longitudinal medical history will appear here."
          actionText="Register First Patient"
          actionLink="/patients/register"
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* LEFT: Patient Selector & Search (4 cols) */}
          <div className="lg:col-span-4 space-y-4">
            <div className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-xs">
              <div className="relative mb-3">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Search className="w-4 h-4" />
                </div>
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Filter by name, ID, phone..."
                  className="w-full pl-9 pr-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-800 placeholder-slate-400 focus:outline-hidden focus:border-blue-500"
                />
              </div>

              <div className="max-h-[500px] overflow-y-auto space-y-1.5 pr-1">
                {filteredPatients.length === 0 ? (
                  <p className="text-xs text-center text-slate-400 py-6">
                    No matching patients found.
                  </p>
                ) : (
                  filteredPatients.map((p) => {
                    const isSelected = p.patientId === selectedPatientId;
                    return (
                      <button
                        key={p.patientId}
                        onClick={() => setSelectedPatientId(p.patientId)}
                        className={`w-full text-left p-3 rounded-xl transition flex items-center justify-between gap-2 cursor-pointer ${
                          isSelected
                            ? 'bg-blue-50 border border-blue-200 text-blue-900 shadow-2xs'
                            : 'hover:bg-slate-50 border border-transparent text-slate-700'
                        }`}
                      >
                        <div className="min-w-0">
                          <p className="font-bold text-xs truncate">{p.patientName}</p>
                          <div className="flex items-center gap-1.5 text-[11px] text-slate-400 font-mono mt-0.5">
                            <span>{p.patientId}</span>
                            <span>•</span>
                            <span>{p.visits?.length || 1} visits</span>
                          </div>
                        </div>
                        <SeverityBadge severity={p.currentSeverity || p.severity} size="sm" />
                      </button>
                    );
                  })
                )}
              </div>
            </div>
          </div>

          {/* RIGHT: Selected Patient Timeline & History (8 cols) */}
          <div className="lg:col-span-8 space-y-6">
            {!selectedPatient ? (
              <div className="bg-white rounded-3xl p-8 border border-slate-200/80 text-center">
                <p className="text-slate-400 text-xs">
                  Select a patient from the directory on the left to view their medical history.
                </p>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Patient Summary Header */}
                <div className="bg-white rounded-3xl p-6 border border-slate-200/80 shadow-xs">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-mono text-xs font-bold bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                          {selectedPatient.patientId}
                        </span>
                        <PatientTypeBadge type={selectedPatient.patientType} />
                      </div>
                      <h3 className="text-xl font-bold text-slate-900">
                        {selectedPatient.patientName}
                      </h3>
                      <p className="text-xs text-slate-500 mt-0.5">
                        {selectedPatient.age} yrs • {selectedPatient.gender || 'N/A'} • Contact: {selectedPatient.phoneNumber}
                      </p>
                    </div>

                    <Link
                      to={`/priority/${selectedPatient.patientId}`}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-blue-50 text-blue-700 hover:bg-blue-100 text-xs font-semibold transition self-start"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>View Triage</span>
                    </Link>
                  </div>

                  {/* Current / Latest Visit Overview */}
                  <div className="pt-4 space-y-2">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block">
                      Current Visit Snapshot
                    </span>
                    <div className="p-3.5 rounded-2xl bg-blue-50/50 border border-blue-100 grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                      <div>
                        <span className="text-slate-400 block text-[10px]">Current Symptoms</span>
                        <strong className="text-slate-800">
                          {Array.isArray(selectedPatient.symptoms)
                            ? selectedPatient.symptoms.join(', ')
                            : selectedPatient.symptoms || 'None'}
                        </strong>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px]">Current Priority</span>
                        <PriorityScoreBadge score={selectedPatient.currentPriority || selectedPatient.priorityScore} />
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px]">Current Severity</span>
                        <SeverityBadge severity={selectedPatient.currentSeverity || selectedPatient.severity} size="sm" />
                      </div>
                    </div>
                  </div>
                </div>

                {/* TIMELINE OF PREVIOUS VISITS */}
                <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200/80 shadow-xs space-y-6">
                  <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
                    <History className="w-5 h-5 text-blue-600" />
                    <h4 className="text-base font-bold text-slate-900">
                      Previous Visits Timeline
                    </h4>
                  </div>

                  {visits.length === 0 ? (
                    <p className="text-xs text-slate-400 italic py-6 text-center">
                      No previous visits found.
                    </p>
                  ) : (
                    <div className="relative pl-6 space-y-6 border-l-2 border-blue-100 ml-2">
                      {visits.map((visit, index) => (
                        <div key={visit.visitId || index} className="relative group">
                          {/* Timeline Dot */}
                          <div className="absolute -left-[31px] top-1.5 w-4 h-4 rounded-full bg-blue-600 border-4 border-white shadow-xs" />

                          {/* Visit Card */}
                          <div className="bg-slate-50 hover:bg-white rounded-2xl p-5 border border-slate-200/80 transition shadow-2xs space-y-3">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <div className="flex items-center gap-2">
                                <span className="font-bold text-slate-900 text-sm">
                                  Visit #{visits.length - index}
                                </span>
                                <span className="text-xs text-slate-400 flex items-center gap-1 font-medium">
                                  <Calendar className="w-3.5 h-3.5" />
                                  {visit.visitDate} {visit.visitTime ? `• ${visit.visitTime}` : ''}
                                </span>
                              </div>
                              <span
                                className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                                  visit.status === 'Consulted'
                                    ? 'bg-emerald-100 text-emerald-800'
                                    : 'bg-amber-100 text-amber-800'
                                }`}
                              >
                                {visit.status === 'Consulted' ? 'Consultation Completed' : 'Awaiting / Active'}
                              </span>
                            </div>

                            {/* Symptoms & Vitals */}
                            <div className="text-xs space-y-1 text-slate-600">
                              <p>
                                <strong>Reported Symptoms:</strong>{' '}
                                {Array.isArray(visit.symptoms) ? visit.symptoms.join(', ') : visit.symptoms}
                              </p>
                              <div className="flex items-center gap-2 text-[11px] text-slate-400">
                                <span>HR: {visit.heartRate} bpm</span>
                                <span>•</span>
                                <span>SpO2: {visit.spo2}%</span>
                                <span>•</span>
                                <span>BP: {visit.bloodPressure}</span>
                                <span>•</span>
                                <span>Temp: {visit.temperature}°F</span>
                              </div>
                            </div>

                            {/* Diagnosis if consulted */}
                            {visit.diagnosis && (
                              <div className="p-3 rounded-xl bg-blue-50/70 border border-blue-100 text-xs">
                                <span className="font-bold text-blue-900 block mb-0.5">
                                  Clinical Diagnosis:
                                </span>
                                <p className="text-blue-800 font-medium">{visit.diagnosis}</p>
                              </div>
                            )}

                            {/* Prescription list if available */}
                            {visit.prescription && visit.prescription.length > 0 && (
                              <div className="pt-2">
                                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                                  Prescribed Medications:
                                </span>
                                <div className="space-y-1">
                                  {visit.prescription.map((rx, rxi) => (
                                    <div
                                      key={rxi}
                                      className="flex items-center justify-between text-xs bg-white p-2 rounded-lg border border-slate-200/60"
                                    >
                                      <span className="font-semibold text-slate-800">
                                        💊 {rx.medicine}
                                      </span>
                                      <span className="text-slate-500 font-mono text-[11px]">
                                        {rx.dosage} • {rx.frequency} ({rx.duration})
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Doctor Notes */}
                            {visit.doctorNotes && (
                              <div className="text-xs text-slate-500 pt-1 italic">
                                <strong>Doctor Advice:</strong> {visit.doctorNotes}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
