import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  HeartPulse,
  Mail,
  Lock,
  User,
  Shield,
  Eye,
  EyeOff,
  AlertCircle,
  ArrowRight,
} from 'lucide-react';

export default function Signup() {
  const navigate = useNavigate();
  const { signup, isAuthenticated } = useAuth();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [role, setRole] = useState('Doctor');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  React.useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');

    // Validation
    if (!name.trim()) {
      setError('Full Name is required.');
      return;
    }
    if (!email.trim() || !/\S+@\S+\.\S+/.test(email)) {
      setError('A valid email address is required.');
      return;
    }
    if (!password || password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setIsSubmitting(true);
    const result = signup({ name, email, password, role });
    setIsSubmitting(false);

    if (result.success) {
      navigate('/dashboard');
    } else {
      setError(result.error || 'Failed to create account.');
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Glow effects */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-600/15 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-indigo-600/15 rounded-full blur-3xl pointer-events-none" />

      <div className="max-w-md w-full relative z-10">
        {/* Brand Header */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-linear-to-tr from-blue-600 to-indigo-500 text-white shadow-xl shadow-blue-500/30 mb-3 animate-pulse-subtle">
            <HeartPulse className="w-7 h-7" />
          </div>
          <div className="flex items-center justify-center gap-2 mb-1">
            <h1 className="text-2xl font-black tracking-tight text-white font-sans">
              MEDQUEUE
            </h1>
            <span className="px-1.5 py-0.5 rounded-md bg-blue-500/20 text-blue-400 text-xs font-mono font-bold tracking-wider border border-blue-500/30">
              AI
            </span>
          </div>
          <p className="text-xs text-slate-400">
            Create Clinical Staff or Physician Account
          </p>
        </div>

        {/* Signup Card */}
        <div className="bg-white rounded-3xl p-6 sm:p-8 shadow-2xl border border-slate-100">
          <div className="mb-5">
            <h2 className="text-xl font-bold text-slate-900">Create Account</h2>
            <p className="text-xs text-slate-500 mt-1">
              Register as clinical staff to start prioritizing and triaging patients.
            </p>
          </div>

          {error && (
            <div className="mb-4 p-3 rounded-xl bg-rose-50 border border-rose-200 flex items-center gap-2 text-rose-700 text-xs font-medium">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-3.5">
            {/* Full Name */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Full Name
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <User className="w-4 h-4" />
                </div>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Dr. Emily Chen"
                  className="w-full pl-10 pr-4 py-2 rounded-xl border border-slate-200 text-sm text-slate-800 placeholder-slate-400 focus:outline-hidden focus:border-blue-500 focus:ring-3 focus:ring-blue-500/10 transition"
                />
              </div>
            </div>

            {/* Email Address */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
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
                  placeholder="chen@hospital.org"
                  className="w-full pl-10 pr-4 py-2 rounded-xl border border-slate-200 text-sm text-slate-800 placeholder-slate-400 focus:outline-hidden focus:border-blue-500 focus:ring-3 focus:ring-blue-500/10 transition"
                />
              </div>
            </div>

            {/* Role Selector */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Role / Function
              </label>
              <div className="grid grid-cols-3 gap-2">
                {['Doctor', 'Receptionist', 'Admin'].map((r) => (
                  <button
                    key={r}
                    type="button"
                    onClick={() => setRole(r)}
                    className={`py-2 px-2 text-xs font-semibold rounded-xl border transition cursor-pointer ${
                      role === r
                        ? 'bg-blue-50 border-blue-600 text-blue-700 shadow-2xs'
                        : 'border-slate-200 text-slate-600 hover:border-slate-300'
                    }`}
                  >
                    {r === 'Doctor' ? '👨‍⚕️ ' : r === 'Receptionist' ? '📋 ' : '🛡️ '}
                    {r}
                  </button>
                ))}
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Password (min. 6 characters)
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-10 pr-10 py-2 rounded-xl border border-slate-200 text-sm text-slate-800 placeholder-slate-400 focus:outline-hidden focus:border-blue-500 focus:ring-3 focus:ring-blue-500/10 transition"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-600 transition"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Confirm Password */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Confirm Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-10 pr-4 py-2 rounded-xl border border-slate-200 text-sm text-slate-800 placeholder-slate-400 focus:outline-hidden focus:border-blue-500 focus:ring-3 focus:ring-blue-500/10 transition"
                />
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm shadow-md shadow-blue-500/25 transition active:scale-98 cursor-pointer flex items-center justify-center gap-2 mt-4"
            >
              <span>Create Account</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          {/* Sign In Link */}
          <div className="text-center mt-5 pt-4 border-t border-slate-100">
            <p className="text-xs text-slate-500">
              Already have an account?{' '}
              <Link to="/login" className="font-bold text-blue-600 hover:text-blue-700">
                Sign In
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
