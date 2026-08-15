import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Bot, LogOut, Bell, User } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { Badge } from '../common/Badge';

export const Navbar: React.FC = () => {
  const { user, role, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  const normalizedRole = role?.toUpperCase();

  return (
    <header className="h-16 bg-slate-900 border-b border-slate-800 px-6 flex items-center justify-between sticky top-0 z-40">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-indigo-600/20 border border-indigo-500/30 rounded-xl text-indigo-400">
          <Bot className="w-5 h-5" />
        </div>
        <div>
          <span className="text-sm font-bold text-white tracking-wide">Allocation AI</span>
          <span className="hidden sm:inline-block ml-2 text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded border border-slate-700 font-mono">
            v2.4 Engine
          </span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {normalizedRole && (
          <Badge
            label={`${normalizedRole} VIEW`}
            variant={
              normalizedRole === 'ADMIN'
                ? 'indigo'
                : normalizedRole === 'EMPLOYEE'
                ? 'emerald'
                : 'amber'
            }
            size="md"
          />
        )}

        <button
          type="button"
          aria-label="Notifications"
          className="text-slate-400 hover:text-white p-2 rounded-xl hover:bg-slate-800 relative"
        >
          <Bell className="w-4 h-4" />
          <span className="absolute top-2 right-2 flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500" />
          </span>
        </button>

        <div className="h-6 w-[1px] bg-slate-800" />

        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300">
            <User className="w-4 h-4" />
          </div>
          <div className="hidden md:block text-left">
            <p className="text-xs font-semibold text-white">{user?.name || 'User'}</p>
            <p className="text-[10px] text-slate-400 truncate max-w-[120px]">{user?.email}</p>
          </div>
        </div>

        <button
          type="button"
          onClick={handleLogout}
          title="Logout"
          className="text-slate-400 hover:text-rose-400 p-2 rounded-xl hover:bg-rose-500/10 transition-colors"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};