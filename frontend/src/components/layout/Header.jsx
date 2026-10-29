import React, { useState } from 'react';
import { useLocation, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useApp } from '../../context/AppContext';
import {
  Menu,
  Bell,
  Calendar,
  UserPlus,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Sparkles,
  ChevronDown,
} from 'lucide-react';

const PAGE_TITLES = {
  '/dashboard': { title: 'Triage Dashboard', subtitle: 'Live Patient Prioritization & OP Queue' },
  '/patients/register': { title: 'Patient Registration', subtitle: 'OP Ticket & Clinical Intake' },
  '/priority-queue': { title: 'Live Priority Queue', subtitle: 'Real-time Outpatient Waiting List' },
  '/patients/history': { title: 'Patient Medical History', subtitle: 'Longitudinal Patient Visit Archives' },
  '/doctor': { title: 'Doctor Consultation Desk', subtitle: 'Attending Physician Workspace' },
  '/consultation': { title: 'Clinical Consultation', subtitle: 'Diagnosis, Prescriptions & Notes' },
  '/profile': { title: 'Staff Profile', subtitle: 'Account & Clinical Credentials' },
};

export default function Header({ onOpenMobile }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { dailyStats, queue, toasts } = useApp();
  const [showNotifications, setShowNotifications] = useState(false);

  // Match title or dynamic params
  let currentMeta = PAGE_TITLES[location.pathname];
  if (!currentMeta) {
    if (location.pathname.startsWith('/priority/')) {
      currentMeta = { title: 'AI Priority Assessment', subtitle: 'Simulated Patient Triage Evaluation' };
    } else if (location.pathname.startsWith('/consultation/')) {
      currentMeta = { title: 'Active Consultation', subtitle: 'Clinical Examination & Prescription' };
    } else if (location.pathname.includes('/history')) {
      currentMeta = { title: 'Patient Visit History', subtitle: 'Previous Records & Consultations' };
    } else if (location.pathname.startsWith('/patients/')) {
      currentMeta = { title: 'Patient Medical Details', subtitle: 'Patient Profile & Clinical Summary' };
    } else {
      currentMeta = { title: 'MedQueue AI', subtitle: 'Smart Patient Prioritization' };
    }
  }

  return (
    <header className="sticky top-0 z-30 bg-white/90 backdrop-blur-md border-b border-slate-200/80 px-4 sm:px-8 py-3.5 flex items-center justify-between transition-all">
      {/* Left: Mobile hamburger & Page Title */}
      <div className="flex items-center gap-3.5">
        <button
          onClick={onOpenMobile}
          className="lg:hidden p-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition"
          aria-label="Toggle navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight leading-none">
            {currentMeta.title}
          </h1>
          <p className="text-xs text-slate-500 font-medium hidden sm:block mt-1">
            {currentMeta.subtitle}
          </p>
        </div>
      </div>

      {/* Right: Date, Quick Action, Notifications, User Pill */}
      <div className="flex items-center gap-2 sm:gap-4">
        {/* Current Date Display */}
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200/70 text-slate-700 text-xs font-medium shadow-2xs">
          <Calendar className="w-3.5 h-3.5 text-blue-600" />
          <span>{dailyStats.displayDate}</span>
        </div>

        {/* Quick Patient Registration Button */}
        {location.pathname !== '/patients/register' && (
          <Link
            to="/patients/register"
            className="hidden sm:inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl shadow-xs shadow-blue-500/20 transition active:scale-95 cursor-pointer"
          >
            <UserPlus className="w-3.5 h-3.5" />
            <span>New Patient</span>
          </Link>
        )}

        {/* Notification Bell Dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative p-2 rounded-xl text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition"
            aria-label="View notifications"
          >
            <Bell className="w-5 h-5" />
            {queue.length > 0 && (
              <span className="absolute top-1.5 right-1.5 flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
              </span>
            )}
          </button>

          {showNotifications && (
            <div
              className="absolute right-0 mt-2 w-80 bg-white rounded-2xl shadow-xl border border-slate-200 py-3 z-50 animate-in fade-in zoom-in-95"
              onMouseLeave={() => setShowNotifications(false)}
            >
              <div className="px-4 py-2 border-b border-slate-100 flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Triage Live Alerts
                </span>
                <span className="text-[11px] font-semibold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full">
                  {queue.length} in queue
                </span>
              </div>

              <div className="max-h-64 overflow-y-auto p-2 space-y-1">
                {queue.length === 0 ? (
                  <p className="text-xs text-center text-slate-400 py-6">
                    No active waiting queue alerts.
                  </p>
                ) : (
                  queue.slice(0, 4).map((item) => (
                    <div
                      key={item.patientId}
                      onClick={() => {
                        setShowNotifications(false);
                        navigate('/priority-queue');
                      }}
                      className="p-2.5 rounded-xl hover:bg-slate-50 transition cursor-pointer flex items-start gap-2.5 text-left"
                    >
                      <div className={`p-1.5 rounded-lg shrink-0 ${
                        item.severity === 'HIGH' ? 'bg-rose-100 text-rose-600' : 'bg-blue-100 text-blue-600'
                      }`}>
                        <Activity className="w-3.5 h-3.5" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between">
                          <p className="text-xs font-bold text-slate-800 truncate">
                            {item.patientName}
                          </p>
                          <span className="text-[10px] font-mono text-slate-400">
                            {item.patientId}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-500">
                          Priority Score: {item.priorityScore} • {item.severity}
                        </p>
                      </div>
                    </div>
                  ))
                )}
              </div>

              <div className="px-4 pt-2 border-t border-slate-100 text-center">
                <Link
                  to="/priority-queue"
                  onClick={() => setShowNotifications(false)}
                  className="text-xs font-semibold text-blue-600 hover:text-blue-700"
                >
                  View Full Priority Queue →
                </Link>
              </div>
            </div>
          )}
        </div>

        {/* User Pill */}
        <Link
          to="/profile"
          className="flex items-center gap-2 pl-2 pr-3 py-1.5 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200/70 transition"
        >
          <div className="w-7 h-7 rounded-lg bg-blue-600 text-white font-bold text-xs flex items-center justify-center shadow-2xs">
            {user?.name ? user.name.charAt(0).toUpperCase() : 'U'}
          </div>
          <div className="hidden sm:block text-left">
            <p className="text-xs font-bold text-slate-800 leading-tight">
              {user?.name || 'Staff'}
            </p>
            <p className="text-[10px] text-slate-400 leading-tight">
              {user?.role || 'Doctor'}
            </p>
          </div>
        </Link>
      </div>
    </header>
  );
}
