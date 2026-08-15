import React from 'react';
import { Card } from '../../components/common/Card';
import { Video, Plus } from 'lucide-react';

export const WebinarManagement: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white">Webinar & Workshop Management</h1>
          <p className="text-slate-400 text-sm">Schedule technical workshops and assign employee speakers.</p>
        </div>
        <button className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-2.5 rounded-xl flex items-center gap-2">
          <Plus className="w-4 h-4" /> Schedule Workshop
        </button>
      </div>

      <Card title="Scheduled Workshops">
        <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl flex justify-between items-center">
          <div className="flex items-center gap-3">
            <Video className="w-5 h-5 text-indigo-400" />
            <div>
              <h4 className="font-bold text-white text-sm">Advanced PyTorch & CUDA Tuning</h4>
              <p className="text-xs text-slate-400">Speaker: Dr. Sarah Jenkins • Aug 24, 2026</p>
            </div>
          </div>
          <span className="text-xs text-emerald-400 font-mono font-bold">Confirmed</span>
        </div>
      </Card>
    </div>
  );
};