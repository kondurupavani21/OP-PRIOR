import React from 'react';
import { AlertCircle, AlertTriangle, CheckCircle, ShieldAlert } from 'lucide-react';

export function SeverityBadge({ severity, size = 'md' }) {
  const s = String(severity || 'LOW').toUpperCase();
  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs font-semibold';

  if (s === 'HIGH') {
    return (
      <span className={`inline-flex items-center gap-1.5 rounded-full bg-rose-50 text-rose-700 border border-rose-200/80 shadow-xs ${sizeClasses}`}>
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
        </span>
        HIGH
      </span>
    );
  }

  if (s === 'MEDIUM') {
    return (
      <span className={`inline-flex items-center gap-1.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200/80 shadow-xs ${sizeClasses}`}>
        <span className="inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
        MEDIUM
      </span>
    );
  }

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200/80 shadow-xs ${sizeClasses}`}>
      <span className="inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
      LOW
    </span>
  );
}

export function PriorityScoreBadge({ score }) {
  const num = Number(score) || 0;
  let bg = 'bg-emerald-50 text-emerald-700 border-emerald-200';
  if (num >= 80) bg = 'bg-rose-50 text-rose-700 border-rose-200';
  else if (num >= 50) bg = 'bg-amber-50 text-amber-700 border-amber-200';

  return (
    <span className={`inline-flex items-center font-mono font-bold px-2.5 py-0.5 rounded-md border text-sm ${bg}`}>
      {num}/100
    </span>
  );
}

export function EmergencyRiskBadge({ emergencyRisk }) {
  const isEmergency = emergencyRisk === 'YES' || emergencyRisk === true;
  if (isEmergency) {
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-red-100 text-red-700 text-xs font-bold border border-red-300 animate-pulse">
        <ShieldAlert className="w-4 h-4 text-red-600" />
        EMERGENCY RISK: YES
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 text-slate-600 text-xs font-medium border border-slate-200">
      <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
      EMERGENCY RISK: NO
    </span>
  );
}

export function PatientTypeBadge({ type }) {
  const isExisting = String(type || '').toLowerCase().includes('existing');
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
        isExisting
          ? 'bg-purple-50 text-purple-700 border border-purple-200'
          : 'bg-blue-50 text-blue-700 border border-blue-200'
      }`}
    >
      {isExisting ? 'Existing Patient' : 'New Visit'}
    </span>
  );
}
