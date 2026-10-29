import React from 'react';
import { useApp } from '../../context/AppContext';
import { Activity, ShieldAlert, AlertTriangle, CheckCircle } from 'lucide-react';

export default function QueueSeverityOverview() {
  const { queueSeverityCounts } = useApp();
  const { high, medium, low, total } = queueSeverityCounts;

  const highPct = total > 0 ? Math.round((high / total) * 100) : 0;
  const mediumPct = total > 0 ? Math.round((medium / total) * 100) : 0;
  const lowPct = total > 0 ? Math.round((low / total) * 100) : 0;

  return (
    <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs h-full flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-xl bg-blue-50 text-blue-600 border border-blue-100">
              <Activity className="w-4 h-4" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-slate-900">Queue Overview</h4>
              <p className="text-xs text-slate-400">Severity Distribution Breakdown</p>
            </div>
          </div>
          <span className="text-xs font-mono font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
            {total} Active
          </span>
        </div>

        {/* Visual Progress Bar */}
        <div className="w-full h-3 rounded-full bg-slate-100 overflow-hidden flex mb-5 p-0.5 border border-slate-200/60">
          {total === 0 ? (
            <div className="w-full h-full bg-slate-200 rounded-full" />
          ) : (
            <>
              {high > 0 && (
                <div
                  style={{ width: `${highPct}%` }}
                  className="h-full bg-rose-500 rounded-l-full transition-all duration-500"
                  title={`HIGH Severity: ${high} (${highPct}%)`}
                />
              )}
              {medium > 0 && (
                <div
                  style={{ width: `${mediumPct}%` }}
                  className="h-full bg-amber-500 transition-all duration-500"
                  title={`MEDIUM Severity: ${medium} (${mediumPct}%)`}
                />
              )}
              {low > 0 && (
                <div
                  style={{ width: `${lowPct}%` }}
                  className="h-full bg-emerald-500 rounded-r-full transition-all duration-500"
                  title={`LOW Severity: ${low} (${lowPct}%)`}
                />
              )}
            </>
          )}
        </div>

        {/* Severity Metrics Rows */}
        <div className="space-y-2.5">
          {/* HIGH */}
          <div className="flex items-center justify-between p-2.5 rounded-xl bg-rose-50/60 border border-rose-100/80">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-rose-600" />
              <span className="text-xs font-bold text-rose-900">HIGH Priority / Emergency</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-extrabold text-rose-700 font-sans">{high}</span>
              <span className="text-[10px] text-rose-400 font-mono">({highPct}%)</span>
            </div>
          </div>

          {/* MEDIUM */}
          <div className="flex items-center justify-between p-2.5 rounded-xl bg-amber-50/60 border border-amber-100/80">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
              <span className="text-xs font-bold text-amber-900">MEDIUM Priority</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-extrabold text-amber-700 font-sans">{medium}</span>
              <span className="text-[10px] text-amber-500 font-mono">({mediumPct}%)</span>
            </div>
          </div>

          {/* LOW */}
          <div className="flex items-center justify-between p-2.5 rounded-xl bg-emerald-50/60 border border-emerald-100/80">
            <div className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-emerald-600" />
              <span className="text-xs font-bold text-emerald-900">LOW Priority / Routine</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-extrabold text-emerald-700 font-sans">{low}</span>
              <span className="text-[10px] text-emerald-500 font-mono">({lowPct}%)</span>
            </div>
          </div>
        </div>
      </div>

      <p className="text-[11px] text-slate-400 text-center mt-3 pt-3 border-t border-slate-100">
        Updated in real-time based on dynamic triage calculations.
      </p>
    </div>
  );
}
