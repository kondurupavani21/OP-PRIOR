import React, { useState, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { sortQueue, filterQueue } from '../utils/queueUtils';
import { calculateWaitingTime } from '../utils/timeUtils';
import { SeverityBadge, PriorityScoreBadge, PatientTypeBadge } from '../components/common/Badge';
import EmptyState from '../components/common/EmptyState';
import {
  Search,
  Filter,
  ArrowUpDown,
  Clock,
  Stethoscope,
  Eye,
  History,
  AlertTriangle,
  UserPlus,
  Activity,
  HeartPulse,
  Wind,
} from 'lucide-react';

export default function PriorityQueue() {
  const navigate = useNavigate();
  const { queue, initiateCallPatient, timeTick } = useApp();

  // Filter & Sort State
  const [search, setSearch] = useState('');
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [patientTypeFilter, setPatientTypeFilter] = useState('ALL');
  const [sortBy, setSortBy] = useState('priority'); // 'priority' | 'waitingTime' | 'fcfs'

  // Filtered & Sorted Active Queue
  const processedQueue = useMemo(() => {
    const filtered = filterQueue(queue, {
      search,
      severity: severityFilter,
      patientType: patientTypeFilter,
    });
    return sortQueue(filtered, sortBy);
  }, [queue, search, severityFilter, patientTypeFilter, sortBy, timeTick]);

  return (
    <div className="space-y-6">
      {/* Top Header & Summary */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
            Active Priority Queue
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Real-time outpatient waiting list prioritized dynamically by clinical severity score and wait time.
          </p>
        </div>

        <Link
          to="/patients/register"
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs shadow-md shadow-blue-500/20 transition active:scale-95 cursor-pointer self-start"
        >
          <UserPlus className="w-4 h-4" />
          <span>Register New Patient</span>
        </Link>
      </div>

      {/* SEARCH, FILTER & SORT BAR */}
      <div className="bg-white rounded-2xl p-4 sm:p-5 border border-slate-200/80 shadow-xs space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {/* Search Box */}
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
              <Search className="w-4 h-4" />
            </div>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search Name, ID, Phone..."
              className="w-full pl-10 pr-4 py-2 rounded-xl border border-slate-200 text-xs text-slate-800 placeholder-slate-400 focus:outline-hidden focus:border-blue-500 transition"
            />
          </div>

          {/* Severity Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-400 shrink-0" />
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-700 focus:outline-hidden focus:border-blue-500 bg-white"
            >
              <option value="ALL">All Severities</option>
              <option value="HIGH">HIGH Severity Only</option>
              <option value="MEDIUM">MEDIUM Severity Only</option>
              <option value="LOW">LOW Severity Only</option>
            </select>
          </div>

          {/* Patient Type Filter */}
          <div>
            <select
              value={patientTypeFilter}
              onChange={(e) => setPatientTypeFilter(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-700 focus:outline-hidden focus:border-blue-500 bg-white"
            >
              <option value="ALL">All Patient Types</option>
              <option value="New">New Patients Only</option>
              <option value="Existing">Existing Patients Only</option>
            </select>
          </div>

          {/* Sorting Method */}
          <div className="flex items-center gap-2">
            <ArrowUpDown className="w-4 h-4 text-slate-400 shrink-0" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-700 focus:outline-hidden focus:border-blue-500 bg-white"
            >
              <option value="priority">Sort: Highest Priority Score</option>
              <option value="waitingTime">Sort: Longest Waiting Time</option>
              <option value="fcfs">Sort: Arrival Order (FCFS)</option>
            </select>
          </div>
        </div>

        {/* Active Filters summary */}
        <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-xs text-slate-400">
          <span>
            Showing <strong>{processedQueue.length}</strong> of {queue.length} waiting patients
          </span>
          {(search || severityFilter !== 'ALL' || patientTypeFilter !== 'ALL' || sortBy !== 'priority') && (
            <button
              onClick={() => {
                setSearch('');
                setSeverityFilter('ALL');
                setPatientTypeFilter('ALL');
                setSortBy('priority');
              }}
              className="text-blue-600 hover:text-blue-700 font-semibold cursor-pointer"
            >
              Reset Filters
            </button>
          )}
        </div>
      </div>

      {/* QUEUE TABLE */}
      {processedQueue.length === 0 ? (
        <EmptyState
          icon={Clock}
          title="No patients currently waiting."
          description={
            queue.length === 0
              ? 'The waiting queue is currently clear. Register an outpatient ticket to begin prioritizing.'
              : 'No waiting patients match your active search or filter criteria.'
          }
          actionText={queue.length === 0 ? 'Register Patient' : undefined}
          actionLink={queue.length === 0 ? '/patients/register' : undefined}
        />
      ) : (
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="py-3.5 pl-4 pr-2">#</th>
                  <th className="py-3.5 px-3">Patient Information</th>
                  <th className="py-3.5 px-3">Type</th>
                  <th className="py-3.5 px-3">Severity</th>
                  <th className="py-3.5 px-3">Vitals (SpO2 / HR / BP)</th>
                  <th className="py-3.5 px-3">Waiting Time</th>
                  <th className="py-3.5 px-3">Priority Score</th>
                  <th className="py-3.5 pl-3 pr-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {processedQueue.map((item, index) => {
                  const waitTimeStr = calculateWaitingTime(item.queueEntryTime);
                  const isTop = index === 0;

                  return (
                    <tr
                      key={item.patientId}
                      className={`hover:bg-blue-50/40 transition ${
                        isTop ? 'bg-blue-50/20' : ''
                      }`}
                    >
                      {/* # Number / Badge */}
                      <td className="py-4 pl-4 pr-2 font-mono font-bold">
                        <span
                          className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs ${
                            isTop
                              ? 'bg-blue-600 text-white font-bold'
                              : 'bg-slate-100 text-slate-600'
                          }`}
                        >
                          {index + 1}
                        </span>
                      </td>

                      {/* Patient Name & Details */}
                      <td className="py-4 px-3">
                        <div className="font-bold text-slate-900 text-sm">
                          {item.patientName}
                        </div>
                        <div className="flex items-center gap-1.5 text-[11px] text-slate-400 font-mono mt-0.5">
                          <span>{item.patientId}</span>
                          <span>•</span>
                          <span>{item.age}y</span>
                          <span>•</span>
                          <span>{item.gender || 'N/A'}</span>
                        </div>
                      </td>

                      {/* Patient Type */}
                      <td className="py-4 px-3">
                        <PatientTypeBadge type={item.patientType} />
                      </td>

                      {/* Severity */}
                      <td className="py-4 px-3">
                        <SeverityBadge severity={item.severity} size="sm" />
                      </td>

                      {/* Vitals Summary */}
                      <td className="py-4 px-3">
                        <div className="text-[11px] space-y-0.5 text-slate-600">
                          <div>
                            <span className="text-slate-400">SpO2:</span>{' '}
                            <strong className={Number(item.spo2) < 92 ? 'text-rose-600' : ''}>
                              {item.spo2}%
                            </strong>
                            <span className="mx-1 text-slate-300">|</span>
                            <span className="text-slate-400">HR:</span>{' '}
                            <strong>{item.heartRate} bpm</strong>
                          </div>
                          <div className="text-slate-500 font-mono">
                            BP: {item.bloodPressure || '120/80'}
                          </div>
                        </div>
                      </td>

                      {/* Live Waiting Time */}
                      <td className="py-4 px-3">
                        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-100 font-semibold text-slate-700">
                          <Clock className="w-3.5 h-3.5 text-blue-500" />
                          <span>{waitTimeStr}</span>
                        </div>
                      </td>

                      {/* Priority Score */}
                      <td className="py-4 px-3">
                        <PriorityScoreBadge score={item.priorityScore} />
                      </td>

                      {/* Actions */}
                      <td className="py-4 pl-3 pr-4 text-right">
                        <div className="inline-flex items-center gap-1.5">
                          <button
                            onClick={() => initiateCallPatient(item)}
                            title="Call Patient into consultation"
                            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold transition active:scale-95 cursor-pointer shadow-xs shadow-blue-500/20"
                          >
                            <Stethoscope className="w-3.5 h-3.5" />
                            <span>Call</span>
                          </button>

                          <Link
                            to={`/patients/${item.patientId}`}
                            title="View Patient Details"
                            className="p-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100 transition"
                          >
                            <Eye className="w-4 h-4" />
                          </Link>

                          <Link
                            to={`/patients/${item.patientId}/history`}
                            title="View Longitudinal History"
                            className="p-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100 transition"
                          >
                            <History className="w-4 h-4" />
                          </Link>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
