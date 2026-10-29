import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  HeartPulse,
  Mail,
  Lock,
  Eye,
  EyeOff,
  AlertCircle,
  Stethoscope,
  ShieldCheck,
  ArrowRight,
} from 'lucide-react';

export default function Login() {
  const navigate = useNavigate();
  const { login, quickDemoLogin, isAuthenticated } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // If already logged in, redirect to dashboard
  React.useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');

    if (!email.trim() || !password) {
      setError('Please fill in both email and password.');
      return;
    }

    setIsSubmitting(true);
    const result = login(email, password);
    setIsSubmitting(false);

    if (result.success) {
      navigate('/dashboard');
    } else {
      setError(result.error || 'Invalid credentials.');
    }
  };

  const handleQuickDemo = (role) => {
    quickDemoLogin(role);
    navigate('/dashboard');
  };

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background Decorative Radial Glows */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-600/15 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-indigo-600/15 rounded-full blur-3xl pointer-events-none" />

      <div className="max-w-md w-full relative z-10">
        {/* Brand Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-linear-to-tr from-blue-600 to-indigo-500 text-white shadow-xl shadow-blue-500/30 mb-4 animate-pulse-subtle">
            <HeartPulse className="w-8 h-8" />
          </div>
          <div className="flex items-center justify-center gap-2 mb-1">
            <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-white font-sans">
              MEDQUEUE
            </h1>
            <span className="px-2 py-0.5 rounded-md bg-blue-500/20 text-blue-400 text-xs font-mono font-bold tracking-wider border border-blue-500/30">
              AI
            </span>
          </div>
          <p className="text-sm text-slate-400">
            Smart Patient Prioritization & Outpatient Triage System
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-white rounded-3xl p-6 sm:p-8 shadow-2xl border border-slate-100">
          <div className="mb-6">
            <h2 className="text-xl font-bold text-slate-900">Welcome Back</h2>
            <p className="text-xs text-slate-500 mt-1">
              Sign in to access the clinical triage and queue management system.
            </p>
          </div>

          {error && (
            <div className="mb-5 p-3.5 rounded-xl bg-rose-50 border border-rose-200 flex items-center gap-2.5 text-rose-700 text-xs font-medium">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email Field */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="doctor@medqueue.ai"
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 text-sm text-slate-800 placeholder-slate-400 focus:outline-hidden focus:border-blue-500 focus:ring-3 focus:ring-blue-500/10 transition"
                />
              </div>
            </div>

            {/* Password Field */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-semibold text-slate-700">
                  Password
                </label>
                <a
                  href="#forgot"
                  onClick={(e) => {
                    e.preventDefault();
                    alert('For demonstration purposes, password is password123 or select a Quick Demo Account below.');
                  }}
                  className="text-xs font-medium text-blue-600 hover:text-blue-700"
                >
                  Forgot Password?
                </a>
              </div>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-10 pr-11 py-2.5 rounded-xl border border-slate-200 text-sm text-slate-800 placeholder-slate-400 focus:outline-hidden focus:border-blue-500 focus:ring-3 focus:ring-blue-500/10 transition"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-600 transition"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm shadow-md shadow-blue-500/25 transition active:scale-98 cursor-pointer flex items-center justify-center gap-2 mt-2"
            >
              <span>Sign In</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          {/* Create Account Link */}
          <div className="text-center mt-5 pt-4 border-t border-slate-100">
            <p className="text-xs text-slate-500">
              Don't have an account?{' '}
              <Link to="/signup" className="font-bold text-blue-600 hover:text-blue-700">
                Create Account
              </Link>
            </p>
          </div>

          {/* Quick Demo Access Bar for fast testing */}
          <div className="mt-5 p-3 rounded-2xl bg-slate-50 border border-slate-100">
            <span className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2 text-center">
              Quick One-Click Demo Logins
            </span>
            <div className="grid grid-cols-3 gap-1.5">
              <button
                type="button"
                onClick={() => handleQuickDemo('Doctor')}
                className="py-1.5 px-2 rounded-lg bg-white border border-slate-200 text-[11px] font-semibold text-slate-700 hover:border-blue-400 hover:text-blue-600 shadow-2xs transition cursor-pointer"
              >
                👨‍⚕️ Doctor
              </button>
              <button
                type="button"
                onClick={() => handleQuickDemo('Receptionist')}
                className="py-1.5 px-2 rounded-lg bg-white border border-slate-200 text-[11px] font-semibold text-slate-700 hover:border-blue-400 hover:text-blue-600 shadow-2xs transition cursor-pointer"
              >
                📋 Reception
              </button>
              <button
                type="button"
                onClick={() => handleQuickDemo('Admin')}
                className="py-1.5 px-2 rounded-lg bg-white border border-slate-200 text-[11px] font-semibold text-slate-700 hover:border-blue-400 hover:text-blue-600 shadow-2xs transition cursor-pointer"
              >
                🛡️ Admin
              </button>
            </div>
          </div>
        </div>

        {/* Footer info */}
        <p className="text-center text-[11px] text-slate-500 mt-6">
          MedQueue AI • 100% Frontend Architecture • LocalStorage Enabled
        </p>
      </div>
    </div>
  );
}
