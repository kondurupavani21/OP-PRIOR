import React from 'react';
import { useApp } from '../../context/AppContext';
import { SeverityBadge, PriorityScoreBadge, PatientTypeBadge } from '../common/Badge';
import { User, Phone, Activity, Stethoscope, Clock, ShieldAlert } from 'lucide-react';
import { calculateWaitingTime } from '../../utils/timeUtils';

export default function CurrentPatientCard() {
  const { currentPatient, initiateCallPatient, timeTick } = useApp();

  if (!currentPatient) {
    return (
      <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs flex flex-col items-center justify-center text-center h-full min-h-[260px]">
        <div className="w-12 h-12 rounded-2xl bg-slate-100 text-slate-400 flex items-center justify-center mb-3">
          <User className="w-6 h-6" />
        </div>
        <h4 className="text-base font-bold text-slate-800 mb-1">
          No patients waiting
        </h4>
        <p className="text-xs text-slate-400 max-w-xs">
          The outpatient priority queue is currently clear. New registered patients will automatically appear here.
        </p>
      </div>
    );
  }

  const waitTime = calculateWaitingTime(currentPatient.queueEntryTime);

  return (
    <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs hover:shadow-md transition-all flex flex-col justify-between h-full relative overflow-hidden">
      {/* Decorative top accent line based on severity */}
      <div
        className={`absolute top-0 left-0 right-0 h-1.5 ${
          currentPatient.severity === 'HIGH'
            ? 'bg-rose-500'
            : currentPatient.severity === 'MEDIUM'
            ? 'bg-amber-500'
            : 'bg-emerald-500'
        }`}
      />

      <div>
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-md bg-blue-50 text-blue-700 border border-blue-100 font-mono">
              Current Patient (Top of Queue)
            </span>
            <PatientTypeBadge type={currentPatient.patientType} />
          </div>
          <SeverityBadge severity={currentPatient.severity} />
        </div>

        {/* Patient Identity */}
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="text-xl font-extrabold text-slate-900 tracking-tight">
              {currentPatient.patientName}
            </h3>
            <div className="flex items-center gap-2 text-xs text-slate-500 mt-1">
              <span className="font-mono font-semibold text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded">
                {currentPatient.patientId}
              </span>
              <span>•</span>
              <span>
                {currentPatient.age} yrs • {currentPatient.gender || 'N/A'}
              </span>
            </div>
          </div>

          <div className="text-right">
            <span className="text-[11px] font-semibold text-slate-400 block mb-0.5">
              Priority Score
            </span>
            <PriorityScoreBadge score={currentPatient.priorityScore} />
          </div>
        </div>

        {/* Symptoms & Wait time pills */}
        <div className="grid grid-cols-2 gap-2 text-xs bg-slate-50 rounded-xl p-3 border border-slate-100 mb-4">
          <div>
            <span className="text-slate-400 block text-[10px] uppercase font-semibold">
              Waiting Time
            </span>
            <div className="flex items-center gap-1.5 font-semibold text-slate-700 mt-0.5">
              <Clock className="w-3.5 h-3.5 text-blue-500" />
              <span>{waitTime}</span>
            </div>
          </div>
          <div>
            <span className="text-slate-400 block text-[10px] uppercase font-semibold">
              Symptoms Presenting
            </span>
            <p className="font-semibold text-slate-700 mt-0.5 truncate" title={Array.isArray(currentPatient.symptoms) ? currentPatient.symptoms.join(', ') : currentPatient.symptoms}>
              {Array.isArray(currentPatient.symptoms)
                ? currentPatient.symptoms.join(', ')
                : currentPatient.symptoms || 'Routine checkup'}
            </p>
          </div>
        </div>
      </div>

      {/* Action Button */}
      <button
        onClick={() => initiateCallPatient(currentPatient)}
        className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm shadow-md shadow-blue-500/20 transition active:scale-98 cursor-pointer"
      >
        <Stethoscope className="w-4 h-4" />
        <span>Call Patient</span>
      </button>
    </div>
  );
}
