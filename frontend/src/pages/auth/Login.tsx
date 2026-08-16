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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    console.log('⚡ STEP 1: Form submitted for:', email);

    try {
      console.log('⚡ STEP 2: Sending request to /api/auth/login...');
      
      // Axios wraps the backend payload in .data
      const response = await api.post('/api/auth/login', { email, password });
      
      console.log('⚡ STEP 3: API Response received:', response.data);

      const { user: userData, token } = response.data;

      console.log('⚡ STEP 4: Calling login() in AuthContext...');
      login(userData, token);
      console.log('⚡ STEP 5: AuthContext updated successfully.');

      const role = userData?.role?.toLowerCase();
      console.log('⚡ STEP 6: User role detected as:', role);

      if (role === 'admin') {
        console.log('⚡ STEP 7: Navigating to /admin/overview');
        navigate('/admin/overview', { replace: true });
      } else if (role === 'student' || role === 'intern') {
        console.log('⚡ STEP 7: Navigating to /student/dashboard');
        navigate('/student/dashboard', { replace: true });
      } else {
        console.log('⚡ STEP 7: Navigating to /employee/dashboard');
        navigate('/employee/dashboard', { replace: true });
      }
    } catch (err: any) {
      console.error('❌ STEP ERROR: Login failed with error:', err);
      const msg =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        err?.message ||
        'Invalid email or password. Please try again.';
      setError(msg);
    } finally {
      console.log('⚡ STEP 8: Cleaning up loading state.');
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