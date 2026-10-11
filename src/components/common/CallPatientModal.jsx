import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../../context/AppContext';
import { UserCheck, AlertTriangle, Phone, Stethoscope, X } from 'lucide-react';
import { SeverityBadge, PriorityScoreBadge } from './Badge';

export default function CallPatientModal() {
  const {
    callModalOpen,
    setCallModalOpen,
    patientInCall,
    confirmPatientPresent,
    skipPatient,
  } = useApp();
  const navigate = useNavigate();

  if (!callModalOpen || !patientInCall) return null;

  const handleYes = () => {
    confirmPatientPresent(navigate);
  };

  const handleNo = () => {
    skipPatient(patientInCall.patientId);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs transition-opacity animate-in fade-in">
      <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl border border-slate-100 overflow-hidden transform transition-all scale-100 animate-in zoom-in-95">
        {/* Header with Call Status */}
        <div className="bg-linear-to-r from-blue-600 to-indigo-700 px-6 py-4 text-white flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-white/10 rounded-lg">
              <Stethoscope className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-lg text-white">Call Patient</h3>
              <p className="text-xs text-blue-100">Outpatient Consultation Desk</p>
            </div>
          </div>
          <button
            onClick={() => setCallModalOpen(false)}
            className="p-1 rounded-lg text-white/70 hover:text-white hover:bg-white/10 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          <div className="text-center mb-6">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-blue-50 border border-blue-100 mb-3">
              <UserCheck className="w-7 h-7 text-blue-600" />
            </div>
            <h4 className="text-xl font-bold text-slate-800 mb-1">
              Is patient present?
            </h4>
            <p className="text-sm text-slate-500">
              Please verify if the patient has responded to the triage call chime.
            </p>
          </div>

          {/* Patient Card Preview */}
          <div className="bg-slate-50 rounded-xl p-4 border border-slate-200 mb-6">
            <div className="flex items-start justify-between mb-2">
              <div>
                <span className="text-xs font-mono font-semibold text-blue-700 bg-blue-100/60 px-2 py-0.5 rounded">
                  {patientInCall.patientId}
                </span>
                <h5 className="text-base font-bold text-slate-900 mt-1">
                  {patientInCall.patientName}
                </h5>
              </div>
              <SeverityBadge severity={patientInCall.severity} size="sm" />
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs text-slate-600 mt-3 pt-3 border-t border-slate-200/60">
              <div>
                <span className="text-slate-400">Age / Gender:</span>{' '}
                <span className="font-medium text-slate-700">
                  {patientInCall.age} yrs • {patientInCall.gender || 'N/A'}
                </span>
              </div>
              <div>
                <span className="text-slate-400">Priority:</span>{' '}
                <PriorityScoreBadge score={patientInCall.priorityScore} />
              </div>
              {patientInCall.phoneNumber && (
                <div className="col-span-2 flex items-center gap-1 text-slate-500 mt-1">
                  <Phone className="w-3.5 h-3.5 text-slate-400" />
                  <span>{patientInCall.phoneNumber}</span>
                </div>
              )}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={handleNo}
              className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-slate-300 text-slate-700 font-semibold hover:bg-slate-100 hover:text-slate-900 transition active:scale-95 cursor-pointer"
            >
              <AlertTriangle className="w-4 h-4 text-amber-500" />
              NO (Skip)
            </button>
            <button
              onClick={handleYes}
              className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 text-white font-semibold hover:bg-blue-700 shadow-md shadow-blue-500/20 transition active:scale-95 cursor-pointer"
            >
              <UserCheck className="w-4 h-4" />
              YES (Present)
            </button>
          </div>
          <p className="text-[11px] text-center text-slate-400 mt-3">
            Skipping retains the patient's record and adjusts position in the queue.
          </p>
        </div>
      </div>
    </div>
  );
}
