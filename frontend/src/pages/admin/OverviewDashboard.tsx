import React from 'react';
import { Card } from '../../components/common/Card';
import { Users, GitMerge, CheckCircle, AlertTriangle } from 'lucide-react';

export const OverviewDashboard: React.FC = () => {
  const metrics = [
    { label: 'Total Projects', value: '24', icon: GitMerge, color: 'text-indigo-400' },
    { label: 'Active Candidates', value: '142', icon: Users, color: 'text-emerald-400' },
    { label: 'Successful Allocations', value: '89%', icon: CheckCircle, color: 'text-amber-400' },
    { label: 'Pending Approvals', value: '3', icon: AlertTriangle, color: 'text-rose-400' },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">System Analytics & Overview</h1>
        <p className="text-slate-400 text-sm">High-level metrics across active projects, candidate availability, and match rates.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {metrics.map((m, i) => {
          const Icon = m.icon;
          return (
            <Card key={i}>
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-xs text-slate-400">{m.label}</span>
                  <h3 className="text-2xl font-black text-white mt-1">{m.value}</h3>
                </div>
                <div className={`p-3 bg-slate-950 rounded-xl border border-slate-800 ${m.color}`}>
                  <Icon className="w-6 h-6" />
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
};