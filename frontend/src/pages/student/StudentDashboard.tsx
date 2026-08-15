import React from 'react';
import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { GraduationCap, Award, CheckCircle2 } from 'lucide-react';

export const StudentDashboard: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Intern Portal</h1>
        <p className="text-slate-400 text-sm">View allocated training engagements, skill ratings, and assigned mentor details.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card title="Allocation Status" className="md:col-span-2">
          <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl space-y-4">
            <div className="flex justify-between items-start">
              <div>
                <span className="text-[10px] font-bold text-indigo-400 uppercase">Current Allocation</span>
                <h3 className="text-lg font-bold text-white">Enterprise Search & RAG System</h3>
              </div>
              <Badge label="Allocated" variant="emerald" size="md" />
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              Assigned to internal AI platform project under senior mentorship. Focus: pgvector optimization and FastAPI routing.
            </p>

            <div className="pt-3 border-t border-slate-800 flex justify-between items-center text-xs">
              <span className="text-slate-400">Assigned Mentor: <strong className="text-white">Dr. Sarah Jenkins</strong></span>
              <span className="text-emerald-400 font-mono font-bold">92.1% Match Score</span>
            </div>
          </div>
        </Card>

        <Card title="Skills Profile">
          <div className="space-y-2">
            {['Python', 'FastAPI', 'PyTorch', 'SQL'].map((skill) => (
              <div key={skill} className="flex justify-between items-center p-2 bg-slate-950 rounded-lg border border-slate-800 text-xs">
                <span className="text-slate-200">{skill}</span>
                <span className="text-emerald-400 font-semibold">High</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
};