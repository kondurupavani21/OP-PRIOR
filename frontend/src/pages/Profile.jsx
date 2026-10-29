import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useApp } from '../context/AppContext';
import {
  UserCircle,
  Mail,
  Shield,
  Briefcase,
  Award,
  Save,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';

export default function Profile() {
  const { user, updateProfile } = useAuth();
  const { addToast } = useApp();

  const [name, setName] = useState(user?.name || '');
  const [email, setEmail] = useState(user?.email || '');
  const [role, setRole] = useState(user?.role || 'Doctor');
  const [department, setDepartment] = useState(user?.department || 'General Medicine');
  const [licenseId, setLicenseId] = useState(user?.licenseId || 'MED-78291');
  const [message, setMessage] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!name.trim() || !email.trim()) {
      setMessage('Name and email are required.');
      return;
    }

    const res = updateProfile({
      name: name.trim(),
      email: email.trim(),
      role,
      department: department.trim(),
      licenseId: licenseId.trim(),
    });

    if (res.success) {
      addToast('Profile updated successfully.', 'success');
      setMessage('Profile credentials updated in LocalStorage.');
      setTimeout(() => setMessage(''), 3000);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
          Staff Profile & Credentials
        </h2>
        <p className="text-xs text-slate-500 mt-1">
          Manage your clinical identity, role permissions, and attending department.
        </p>
      </div>

      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200/80 shadow-xs space-y-6">
        {/* User Card Header */}
        <div className="flex items-center gap-4 pb-6 border-b border-slate-100">
          <div className="w-16 h-16 rounded-2xl bg-blue-600 text-white flex items-center justify-center font-extrabold text-2xl shadow-md shadow-blue-500/20">
            {name.charAt(0).toUpperCase() || 'U'}
          </div>
          <div>
            <h3 className="text-xl font-bold text-slate-900">{name || 'Clinical Staff'}</h3>
            <div className="flex items-center gap-2 text-xs text-slate-500 mt-1">
              <span className="px-2 py-0.5 rounded-md bg-blue-50 text-blue-700 font-semibold border border-blue-100">
                {role}
              </span>
              <span>•</span>
              <span>{department}</span>
            </div>
          </div>
        </div>

        {message && (
          <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>{message}</span>
          </div>
        )}

        {/* Profile Edit Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Full Name */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Full Name *
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <UserCircle className="w-4 h-4" />
                </div>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 text-sm text-slate-800 focus:outline-hidden focus:border-blue-500"
                />
              </div>
            </div>

            {/* Email */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Email Address *
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 text-sm text-slate-800 focus:outline-hidden focus:border-blue-500"
                />
              </div>
            </div>

            {/* Role */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Role & Function
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Shield className="w-4 h-4" />
                </div>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 text-sm text-slate-800 focus:outline-hidden focus:border-blue-500 bg-white"
                >
                  <option value="Doctor">Doctor</option>
                  <option value="Receptionist">Receptionist</option>
                  <option value="Admin">Admin</option>
                </select>
              </div>
            </div>

            {/* Department */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Department
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Briefcase className="w-4 h-4" />
                </div>
                <input
                  type="text"
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 text-sm text-slate-800 focus:outline-hidden focus:border-blue-500"
                />
              </div>
            </div>

            {/* License / Staff ID */}
            <div className="sm:col-span-2">
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Medical License / Staff ID
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Award className="w-4 h-4" />
                </div>
                <input
                  type="text"
                  value={licenseId}
                  onChange={(e) => setLicenseId(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 text-sm text-slate-800 focus:outline-hidden focus:border-blue-500 font-mono"
                />
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-100 flex justify-end">
            <button
              type="submit"
              className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm shadow-md shadow-blue-500/20 transition active:scale-95 cursor-pointer"
            >
              <Save className="w-4 h-4" />
              <span>Save Profile Changes</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
