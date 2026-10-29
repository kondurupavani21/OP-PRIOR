import React from 'react';
import { Link } from 'react-router-dom';
import { useApp } from '../../context/AppContext';
import { SeverityBadge, PatientTypeBadge } from '../common/Badge';
import { ArrowRight, UserPlus, Users } from 'lucide-react';

export default function NextPatientCard() {
  const { nextPatient } = useApp();

  if (!nextPatient) {
    return (
      <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs flex flex-col items-center justify-center text-center h-full min-h-[220px]">
        <div className="w-10 h-10 rounded-xl bg-slate-100 text-slate-400 flex items-center justify-center mb-2.5">
          <Users className="w-5 h-5" />
        </div>
        <h4 className="text-sm font-bold text-slate-800 mb-0.5">
          No next patient
        </h4>
        <p className="text-xs text-slate-400 max-w-xs mb-3">
          Only one patient is currently waiting in the outpatient queue.
        </p>
        <Link
          to="/patients/register"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-blue-600 hover:text-blue-700"
        >
          <UserPlus className="w-3.5 h-3.5" />
          <span>Register Another Patient</span>
        </Link>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs hover:shadow-md transition-all flex flex-col justify-between h-full">
      <div>
        <div className="flex items-center justify-between gap-2 mb-2">
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 font-mono">
              Next in Queue
            </span>
            <PatientTypeBadge type={nextPatient.patientType} />
          </div>
          <SeverityBadge severity={nextPatient.severity} size="sm" />
        </div>

        <div className="mt-3">
          <h4 className="text-lg font-bold text-slate-900 tracking-tight">
            {nextPatient.patientName}
          </h4>
          <div className="flex items-center gap-2 text-xs text-slate-500 mt-1">
            <span className="font-mono text-slate-600 font-medium">
              {nextPatient.patientId}
            </span>
            <span>•</span>
            <span>{nextPatient.age} years old</span>
          </div>
        </div>
      </div>

      <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between">
        <span className="text-xs text-slate-400">Position #2 in Queue</span>
        <Link
          to="/priority-queue"
          className="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-700 transition"
        >
          <span>View Queue</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    </div>
  );
}
