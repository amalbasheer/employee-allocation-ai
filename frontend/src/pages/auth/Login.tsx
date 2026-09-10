import React, { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { ShieldCheck, AlertCircle, CheckCircle2 } from 'lucide-react';
import { AlignIQLogo } from '../../components/common/AlignIQLogo';
import api from '../../services/api';

export const Login: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const successMessage = location.state?.message;
  // Capture original route if user was redirected to login
  const from = location.state?.from?.pathname;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await api.post('/api/auth/login', { email, password });
      const { user: userData, token } = response.data;

      // Update AuthContext session state
      login(userData, token);

      // Extract role with metadata fallback
      const rawRole = userData?.role || userData?.user_metadata?.role || '';
      const role = rawRole.toUpperCase();

      // If user came from a protected route, send them back there
      if (from) {
        navigate(from, { replace: true });
        return;
      }

      // Default role-based redirection
      if (role === 'ADMIN') {
        navigate('/admin/overview', { replace: true });
      } else if (role === 'STUDENT' || role === 'INTERN') {
        navigate('/student/dashboard', { replace: true });
      } else {
        navigate('/employee/dashboard', { replace: true });
      }
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        err?.message ||
        'Invalid email or password. Please try again.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-slate-900 border border-slate-800 p-8 rounded-2xl shadow-2xl space-y-6">
        <div className="text-center space-y-2">
          <div className="flex items-center justify-center">
            <AlignIQLogo className="w-6 h-6 text-indigo-400" />
          </div>
          <h1 className="text-xl font-bold text-white tracking-tight">AlignIQ</h1>
          <p className="text-xs text-slate-400">Sign in to access your assigned workspace</p>
        </div>

        {successMessage && (
          <div className="flex items-center gap-2 p-3 bg-emerald-950/50 border border-emerald-800/80 text-emerald-300 text-xs rounded-xl">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
            <span>{successMessage}</span>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 p-3 bg-red-950/50 border border-red-800/80 text-red-300 text-xs rounded-xl">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Email Address
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="alex.morgan@enterprise.ai"
              required
              className="w-full bg-slate-950 border border-slate-800 text-xs text-white px-3 py-2.5 rounded-xl focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              className="w-full bg-slate-950 border border-slate-800 text-xs text-white px-3 py-2.5 rounded-xl focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs rounded-xl shadow-lg shadow-indigo-600/20 flex items-center justify-center gap-2 disabled:opacity-50 transition"
          >
            <ShieldCheck className="w-4 h-4" />
            {loading ? 'Authenticating...' : 'Enter Workspace'}
          </button>
        </form>

        <div className="pt-2 text-center text-xs text-slate-400 border-t border-slate-800/60">
          Need to set up your password?{' '}
          <Link
            to="/activate"
            className="text-indigo-400 hover:text-indigo-300 font-medium transition-colors"
          >
            Activate account
          </Link>
        </div>
      </div>
    </div>
  );
};