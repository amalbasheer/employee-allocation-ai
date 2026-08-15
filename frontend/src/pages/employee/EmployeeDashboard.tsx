import React, { useState } from 'react';
import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Check, X, Clock, Briefcase, Video } from 'lucide-react';

export const EmployeeDashboard: React.FC = () => {
  const [proposals, setProposals] = useState([
    {
      id: 'alloc-1',
      projectTitle: 'LLM Fine-Tuning Pipeline',
      role: 'Lead AI Mentor',
      score: 95.4,
      status: 'proposed',
      description: 'Supervise 2 interns building domain-specific LoRA adapters.',
      dueDate: '24 hours remaining',
    },
  ]);

  const handleAction = (id: string, action: 'accept' | 'reject') => {
    setProposals((prev) =>
      prev.map((p) => (p.id === id ? { ...p, status: action === 'accept' ? 'accepted_by_employee' : 'rejected_by_employee' } : p))
    );
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Employee & Mentor Portal</h1>
        <p className="text-slate-400 text-sm">Manage project proposals, team allocations, and assigned workshops.</p>
      </div>

      {/* Proposals Inbox */}
      <Card title="Incoming Allocation Proposals" subtitle="Review AI match assignments within the 72h SLA window">
        <div className="space-y-4">
          {proposals.map((item) => (
            <div key={item.id} className="p-4 bg-slate-950 border border-slate-800 rounded-xl space-y-3">
              <div className="flex justify-between items-start">
                <div>
                  <h4 className="font-bold text-white">{item.projectTitle}</h4>
                  <span className="text-xs text-indigo-400 font-medium">{item.role}</span>
                </div>
                <Badge label={`${item.score}% Match`} variant="emerald" size="md" />
              </div>

              <p className="text-xs text-slate-300">{item.description}</p>

              <div className="flex items-center justify-between pt-2 border-t border-slate-800 text-xs">
                <span className="text-amber-400 flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" /> {item.dueDate}
                </span>

                {item.status === 'proposed' ? (
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleAction(item.id, 'reject')}
                      className="px-3 py-1.5 bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 rounded-lg font-medium flex items-center gap-1"
                    >
                      <X className="w-3.5 h-3.5" /> Reject
                    </button>
                    <button
                      onClick={() => handleAction(item.id, 'accept')}
                      className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-medium flex items-center gap-1"
                    >
                      <Check className="w-3.5 h-3.5" /> Accept Allocation
                    </button>
                  </div>
                ) : (
                  <Badge
                    label={item.status === 'accepted_by_employee' ? 'Accepted' : 'Declined'}
                    variant={item.status === 'accepted_by_employee' ? 'emerald' : 'rose'}
                  />
                )}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Active Work & Workshops */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card title="Active Projects" subtitle="Currently assigned mentorships">
          <div className="flex items-center gap-3 p-3 bg-slate-950 rounded-xl border border-slate-800">
            <Briefcase className="w-5 h-5 text-indigo-400" />
            <div>
              <h5 className="text-xs font-bold text-white">Computer Vision API</h5>
              <p className="text-[11px] text-slate-400">2 Interns • Milestone 2</p>
            </div>
          </div>
        </Card>

        <Card title="Upcoming Webinars" subtitle="Assigned speaking & training sessions">
          <div className="flex items-center gap-3 p-3 bg-slate-950 rounded-xl border border-slate-800">
            <Video className="w-5 h-5 text-amber-400" />
            <div>
              <h5 className="text-xs font-bold text-white">Advanced PyTorch & CUDA Tuning</h5>
              <p className="text-[11px] text-slate-400">Scheduled: Aug 24, 2026</p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};