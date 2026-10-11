import React from 'react';
import { Link } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import StatCard from '../components/common/StatCard';
import CurrentPatientCard from '../components/dashboard/CurrentPatientCard';
import NextPatientCard from '../components/dashboard/NextPatientCard';
import QueueSeverityOverview from '../components/dashboard/QueueSeverityOverview';
import EmptyState from '../components/common/EmptyState';
import { SeverityBadge, PriorityScoreBadge } from '../components/common/Badge';
import {
  Users,
  Clock,
  ShieldAlert,
  CheckCircle2,
  UserPlus,
  ArrowRight,
  Calendar,
  Sparkles,
  Activity,
  Stethoscope,
} from 'lucide-react';
import { calculateWaitingTime } from '../utils/timeUtils';

export default function Dashboard() {
  const { dailyStats, sortedQueue, consultations, initiateCallPatient } = useApp();

  return (
    <div className="space-y-6">
      {/* Top Banner: Today's Clinical Date & Quick Registration */}
      <div className="bg-linear-to-r from-blue-700 via-blue-600 to-indigo-700 rounded-3xl p-6 sm:p-8 text-white shadow-xl shadow-blue-600/15 relative overflow-hidden">
        {/* Subtle decorative medical cross watermark */}
        <div className="absolute right-4 -bottom-10 opacity-10 pointer-events-none">
          <Stethoscope className="w-64 h-64 text-white" />
        </div>

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2 max-w-xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/15 backdrop-blur-md text-xs font-semibold text-blue-100 border border-white/20">
              <Calendar className="w-3.5 h-3.5 text-blue-200" />
              <span>Today's Live Triage • {dailyStats.displayDate}</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white font-sans">
              Smart Patient Prioritization
            </h2>
            <p className="text-blue-100/90 text-sm leading-relaxed">
              Outpatient triage powered by real-time heuristic clinical vital scoring. Dynamic queue management with zero hardcoded delays.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Link
              to="/patients/register"
              className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-white text-blue-700 font-bold text-sm shadow-md hover:bg-blue-50 transition active:scale-95 cursor-pointer"
            >
              <UserPlus className="w-4 h-4" />
              <span>Register Patient</span>
            </Link>
            <Link
              to="/priority-queue"
              className="inline-flex items-center gap-2 px-4 py-3 rounded-xl bg-blue-800/60 hover:bg-blue-800 text-white font-semibold text-sm border border-white/20 backdrop-blur-sm transition active:scale-95 cursor-pointer"
            >
              <span>View Live Queue</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </div>

      {/* 4 DYNAMIC STAT CARDS (Strictly Filtered by Today's Date) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
        <StatCard
          title="Total Patients"
          value={dailyStats.total}
          subtitle={`Registered today (${dailyStats.displayDate})`}
          icon={Users}
          variant="blue"
          badgeText="Today"
        />
        <StatCard
          title="Waiting Patients"
          value={dailyStats.waiting}
          subtitle="Currently active in triage queue"
          icon={Clock}
          variant="amber"
          badgeText="In Queue"
        />
        <StatCard
          title="Emergency Patients"
          value={dailyStats.emergency}
          subtitle="High severity / Critical priority"
          icon={ShieldAlert}
          variant="rose"
          badgeText="Urgent"
        />
        <StatCard
          title="Consulted Patients"
          value={dailyStats.consulted}
          subtitle="Consultations completed today"
          icon={CheckCircle2}
          variant="emerald"
          badgeText="Completed"
        />
      </div>

      {/* THREE-COLUMN CARDS ROW: Current Patient, Next Patient, Queue Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Card 1: Current Patient (Top of Queue) */}
        <div className="lg:col-span-1">
          <CurrentPatientCard />
        </div>

        {/* Card 2: Next Patient */}
        <div className="lg:col-span-1">
          <NextPatientCard />
        </div>

        {/* Card 3: Queue Severity Overview */}
        <div className="lg:col-span-1">
          <QueueSeverityOverview />
        </div>
      </div>

      {/* ACTIVE QUEUE PREVIEW & RECENT CONSULTATIONS */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Active Queue Table Preview (2 Cols) */}
        <div className="lg:col-span-2 bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-bold text-slate-900">
                Active Priority Queue
              </h3>
              <p className="text-xs text-slate-400">
                Sorted by AI simulated priority score & waiting time
              </p>
            </div>
            <Link
              to="/priority-queue"
              className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1"
            >
              <span>Full Queue</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {sortedQueue.length === 0 ? (
            <EmptyState
              icon={Clock}
              title="No patients currently waiting."
              description="The waiting list is empty. Register a new patient or enter an OP ticket to begin."
              actionText="Register First Patient"
              actionLink="/patients/register"
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-100 text-slate-400 font-semibold uppercase tracking-wider">
                    <th className="pb-3 pl-2">#</th>
                    <th className="pb-3">Patient</th>
                    <th className="pb-3">Severity</th>
                    <th className="pb-3">Priority</th>
                    <th className="pb-3">Waiting</th>
                    <th className="pb-3 pr-2 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {sortedQueue.slice(0, 5).map((patient, index) => (
                    <tr key={patient.patientId} className="hover:bg-slate-50/70 transition">
                      <td className="py-3.5 pl-2 font-mono font-bold text-slate-400">
                        {index + 1}
                      </td>
                      <td className="py-3.5">
                        <div className="font-bold text-slate-800 text-sm">
                          {patient.patientName}
                        </div>
                        <div className="text-[11px] text-slate-400 font-mono">
                          {patient.patientId} • {patient.age} yrs
                        </div>
                      </td>
                      <td className="py-3.5">
                        <SeverityBadge severity={patient.severity} size="sm" />
                      </td>
                      <td className="py-3.5">
                        <PriorityScoreBadge score={patient.priorityScore} />
                      </td>
                      <td className="py-3.5 text-slate-500 font-medium">
                        {calculateWaitingTime(patient.queueEntryTime)}
                      </td>
                      <td className="py-3.5 pr-2 text-right">
                        <button
                          onClick={() => initiateCallPatient(patient)}
                          className="px-3 py-1.5 rounded-lg bg-blue-50 text-blue-600 hover:bg-blue-600 hover:text-white font-semibold transition cursor-pointer text-xs"
                        >
                          Call
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Today's Completed Consultations (1 Col) */}
        <div className="lg:col-span-1 bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  Today's Consultations
                </h3>
                <p className="text-xs text-slate-400">Completed doctor visits</p>
              </div>
              <span className="text-xs font-mono font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700">
                {dailyStats.consulted} Done
              </span>
            </div>

            {consultations.length === 0 ? (
              <div className="text-center py-10">
                <CheckCircle2 className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                <p className="text-xs font-semibold text-slate-600">
                  No consultations completed yet today.
                </p>
                <p className="text-[11px] text-slate-400 mt-1">
                  Completed consultations will appear here automatically.
                </p>
              </div>
            ) : (
              <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
                {consultations.slice(0, 4).map((c) => (
                  <div
                    key={c.id || c.consultationId}
                    className="p-3 rounded-xl bg-slate-50 border border-slate-100"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-xs text-slate-800">
                        {c.patientName}
                      </span>
                      <span className="text-[10px] font-mono text-emerald-600 bg-emerald-100/60 px-1.5 py-0.2 rounded font-semibold">
                        Consulted
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500 mt-1 line-clamp-1">
                      <span className="font-medium text-slate-600">Dx:</span>{' '}
                      {c.diagnosis || 'Clinical evaluation completed'}
                    </p>
                    <div className="text-[10px] text-slate-400 mt-1 flex justify-between">
                      <span>By: {c.doctorName || 'Dr. Sarah Jenkins'}</span>
                      <span className="font-mono">{c.consultationId}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <Link
            to="/doctor"
            className="w-full mt-4 py-2.5 px-4 text-center rounded-xl border border-slate-200 text-slate-700 hover:bg-slate-50 text-xs font-semibold transition"
          >
            Open Doctor Desk
          </Link>
        </div>
      </div>
    </div>
  );
}
