import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  GitMerge, 
  Users, 
  Video, 
  CheckSquare, 
  GraduationCap, 
  DockIcon,
  Clock
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export const Sidebar: React.FC = () => {
  const { role } = useAuth();

  const adminNav = [
    { label: 'Overview', path: '/admin/overview', icon: LayoutDashboard },
    { label: 'Project Allocations', path: '/admin/allocations', icon: GitMerge },
    { label: 'User Management', path: '/admin/users', icon: Users },
    { label: 'Webinars & Workshops', path: '/admin/webinars', icon: Video },
  ];

  const employeeNav = [
    { label: 'My Proposals & Projects', path: '/employee/dashboard', icon: DockIcon },
    { label: 'Availability Check', path: '/employee/availability', icon: Clock },
  
  ];

  const studentNav = [
    { label: 'Intern Allocations', path: '/student/dashboard', icon: GraduationCap },
  ];

  const navItems = role === 'ADMIN' ? adminNav : role === 'EMPLOYEE' ? employeeNav : studentNav;

  return (
    <aside className="w-64 bg-slate-950 border-r border-slate-800 flex flex-col justify-between p-4 shrink-0 min-h-[calc(100vh-4rem)]">
      <div className="space-y-6">
        <div>
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 px-3">
            Navigation Menu
          </span>
          <nav className="mt-2 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                      isActive
                        ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                    }`
                  }
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </nav>
        </div>
      </div>

      <div className="p-3 bg-slate-900/60 border border-slate-800 rounded-xl text-[11px] text-slate-400 space-y-1">
        <span className="font-semibold text-slate-300 block">System Status</span>
        <div className="flex items-center gap-2 text-emerald-400">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          pgvector Engine Active
        </div>
      </div>
    </aside>
  );
};