import React from 'react';
import { Users, Clock, FileText, PlusCircle } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function EmptyState({
  icon: Icon = Users,
  title = 'No records found',
  description = 'There are no active records in the system currently.',
  actionText,
  actionLink,
  onAction,
}) {
  return (
    <div className="flex flex-col items-center justify-center p-8 sm:p-12 text-center bg-white rounded-2xl border border-dashed border-slate-200 shadow-2xs">
      <div className="w-14 h-14 rounded-2xl bg-blue-50/70 border border-blue-100 flex items-center justify-center text-blue-600 mb-4 shadow-2xs">
        <Icon className="w-7 h-7" />
      </div>
      <h4 className="text-base font-bold text-slate-800 mb-1">{title}</h4>
      <p className="text-sm text-slate-500 max-w-sm mb-5 leading-relaxed">
        {description}
      </p>

      {actionText && actionLink && (
        <Link
          to={actionLink}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl shadow-xs shadow-blue-500/20 transition active:scale-95 cursor-pointer"
        >
          <PlusCircle className="w-4 h-4" />
          {actionText}
        </Link>
      )}

      {actionText && onAction && !actionLink && (
        <button
          onClick={onAction}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl shadow-xs shadow-blue-500/20 transition active:scale-95 cursor-pointer"
        >
          <PlusCircle className="w-4 h-4" />
          {actionText}
        </button>
      )}
    </div>
  );
}
