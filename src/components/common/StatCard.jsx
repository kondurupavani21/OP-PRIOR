import React from 'react';

export default function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  variant = 'blue',
  badgeText,
}) {
  const variants = {
    blue: {
      bg: 'bg-blue-50/70',
      text: 'text-blue-600',
      border: 'border-blue-100',
      badge: 'bg-blue-100 text-blue-800',
      glow: 'group-hover:border-blue-300',
    },
    amber: {
      bg: 'bg-amber-50/70',
      text: 'text-amber-600',
      border: 'border-amber-100',
      badge: 'bg-amber-100 text-amber-800',
      glow: 'group-hover:border-amber-300',
    },
    rose: {
      bg: 'bg-rose-50/70',
      text: 'text-rose-600',
      border: 'border-rose-100',
      badge: 'bg-rose-100 text-rose-800',
      glow: 'group-hover:border-rose-300',
    },
    emerald: {
      bg: 'bg-emerald-50/70',
      text: 'text-emerald-600',
      border: 'border-emerald-100',
      badge: 'bg-emerald-100 text-emerald-800',
      glow: 'group-hover:border-emerald-300',
    },
  };

  const style = variants[variant] || variants.blue;

  return (
    <div
      className={`group bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs hover:shadow-md transition-all duration-300 ${style.glow}`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className={`p-3 rounded-xl ${style.bg} ${style.border} border`}>
          <Icon className={`w-6 h-6 ${style.text}`} />
        </div>
        {badgeText && (
          <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${style.badge}`}>
            {badgeText}
          </span>
        )}
      </div>

      <div className="space-y-1">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          {title}
        </p>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-extrabold text-slate-800 font-sans tracking-tight">
            {value}
          </span>
        </div>
        {subtitle && (
          <p className="text-xs text-slate-500 font-normal mt-0.5">
            {subtitle}
          </p>
        )}
      </div>
    </div>
  );
}
