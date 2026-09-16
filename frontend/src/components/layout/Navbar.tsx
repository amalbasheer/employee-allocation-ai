// src/components/Navbar.tsx
import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { LogOut, Bell, User } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { Badge } from '../common/Badge';
import { AlignIQLogo } from '../common/AlignIQLogo';

export const Navbar: React.FC = () => {
  const { user, role, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  // Safely resolve role from auth context, metadata, or localStorage
  const resolveRole = (): string => {
    if (typeof role === 'string' && role.trim()) return role;
    if (user?.role) return user.role;
    if ((user as any)?.user_metadata?.role) return (user as any).user_metadata.role;

    try {
      const stored = localStorage.getItem('user');
      if (stored) {
        const parsed = JSON.parse(stored);
        return parsed.role || parsed.user_metadata?.role || '';
      }
    } catch {
      /* ignore JSON error */
    }
    return '';
  };

  const userMetadata = (user as any)?.user_metadata;
  const activeRole = resolveRole();
  const normalizedRole = activeRole.toUpperCase();
  const userName = userMetadata?.name || user?.name || 'User';

  // Role-based navigation with URL path fail-safe
  const handleLogoClick = () => {
    const currentPath = location.pathname;

    if (normalizedRole.includes('ADMIN') || currentPath.startsWith('/admin')) {
      navigate('/admin/overview');
    } else if (normalizedRole.includes('EMPLOYEE') || currentPath.startsWith('/employee')) {
      navigate('/employee/dashboard');
    } else if (
      normalizedRole.includes('STUDENT') ||
      normalizedRole.includes('INTERN') ||
      currentPath.startsWith('/student')
    ) {
      navigate('/student/dashboard');
    } else {
      // Safe fallback if role and path are both unmapped
      navigate('/admin/overview');
    }
  };

  return (
    <header className="h-16 bg-slate-900 border-b border-slate-800 px-6 flex items-center justify-between sticky top-0 z-40">
      {/* Clickable Logo Section */}
      <div 
        onClick={handleLogoClick}
        className="flex items-center gap-3 cursor-pointer group hover:opacity-90 transition-opacity select-none"
        title="Go to Home Dashboard"
      >
        <AlignIQLogo className="w-6 h-6 text-indigo-400 group-hover:scale-105 transition-transform" />
        <div>
          <span className="text-sm font-bold text-white tracking-wide">AlignIQ</span>
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
              normalizedRole.includes('ADMIN')
                ? 'indigo'
                : normalizedRole.includes('EMPLOYEE')
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
            <p className="text-xs font-semibold text-white">{userName}</p>
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