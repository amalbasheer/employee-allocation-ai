import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { AlignIQLogo } from '../../components/common/AlignIQLogo';
import { ShieldCheck, AlertCircle, KeyRound, ArrowRight } from 'lucide-react';
import api from '../../services/api';

export const ActivateAccount: React.FC = () => {
  const [searchParams] = useSearchParams();
  const urlToken = searchParams.get('token');
  const navigate = useNavigate();

  // State management
  const [activeToken, setActiveToken] = useState<string>(urlToken || '');
  const [userData, setUserData] = useState<{ fullName: string; email: string; role: string } | null>(null);
  
  const [inputToken, setInputToken] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  // Function to verify token with backend
  const verifyToken = async (tokenToVerify: string) => {
    setLoading(true);
    setError('');
    try {
      const res = await api.get(`/api/auth/verify-invite?token=${tokenToVerify}`);
      setUserData(res.data); // Expects { fullName, email, role }
      setActiveToken(tokenToVerify);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid or expired activation token. Please check and try again.');
      setUserData(null);
    } finally {
      setLoading(false);
    }
  };

  // Automatically verify if token is present in URL
  useEffect(() => {
    if (urlToken) {
      verifyToken(urlToken);
    }
  }, [urlToken]);

  // Handle manual token submission
  const handleVerifyCodeSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputToken.trim()) {
      setError('Please enter your activation code.');
      return;
    }
    verifyToken(inputToken.trim());
  };

  // Handle password submission
  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setSubmitting(true);
    setError('');

    try {
      await api.post('/api/auth/activate-account', {
        token: activeToken,
        password,
      });

      // Redirect to login page upon success
      navigate('/login', {
        state: { message: 'Account activated successfully! Please sign in with your credentials.' },
      });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to activate account. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-slate-900 border border-slate-800 p-8 rounded-2xl shadow-2xl space-y-6 text-slate-100">
        
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="flex items-center justify-center">
            <AlignIQLogo className="w-8 h-8 text-indigo-400" />
          </div>
          <h1 className="text-xl font-bold text-white tracking-tight">Account Activation</h1>
          <p className="text-xs text-slate-400">
            {userData ? 'Set up password for your assigned workspace' : 'Enter your invitation code to get started'}
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="flex items-center gap-2 p-3 bg-red-950/50 border border-red-800/80 text-red-300 text-xs rounded-xl">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* STEP 1: If no valid token verified yet, show Activation Code Input */}
        {!userData && (
          <form onSubmit={handleVerifyCodeSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Activation Code / Token
              </label>
              <div className="relative">
                <input
                  type="text"
                  required
                  value={inputToken}
                  onChange={(e) => setInputToken(e.target.value)}
                  placeholder="Paste your code from email"
                  className="w-full bg-slate-950 border border-slate-800 text-xs text-white px-3 py-2.5 rounded-xl focus:outline-none focus:ring-1 focus:ring-indigo-500 pl-9"
                />
                <KeyRound className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs rounded-xl shadow-lg shadow-indigo-600/20 flex items-center justify-center gap-2 disabled:opacity-50 transition"
            >
              {loading ? 'Verifying Code...' : 'Continue'}
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>
        )}

        {/* STEP 2: Show profile info & password setup once token is verified */}
        {userData && (
          <form onSubmit={handlePasswordSubmit} className="space-y-4">
            
            {/* Account Details (Locked / Read-Only) */}
            <div className="bg-slate-950 border border-slate-800 p-3 rounded-xl space-y-1">
              <div className="text-xs font-semibold text-white">{userData.fullName}</div>
              <div className="text-xs text-slate-400">{userData.email}</div>
              <div className="inline-block px-2 py-0.5 text-[10px] font-medium bg-indigo-500/10 text-indigo-400 rounded border border-indigo-500/20 uppercase tracking-wider mt-1">
                Role: {userData.role}
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                New Password
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-slate-950 border border-slate-800 text-xs text-white px-3 py-2.5 rounded-xl focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Confirm Password
              </label>
              <input
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-slate-950 border border-slate-800 text-xs text-white px-3 py-2.5 rounded-xl focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs rounded-xl shadow-lg shadow-indigo-600/20 flex items-center justify-center gap-2 disabled:opacity-50 transition"
            >
              <ShieldCheck className="w-4 h-4" />
              {submitting ? 'Setting Password...' : 'Save Password & Go to Login'}
            </button>
          </form>
        )}

        {/* Footer Navigation Back to Login */}
        <div className="pt-2 text-center text-xs text-slate-400 border-t border-slate-800/60">
          Already activated your account?{' '}
          <Link
            to="/login"
            className="text-indigo-400 hover:text-indigo-300 font-medium transition-colors"
          >
            Sign in
          </Link>
        </div>

      </div>
    </div>
  );
};