import React, { useState, useEffect } from 'react';
import axios from 'axios';

interface ScheduleItem {
  item_id: string;
  entity_type: 'project' | 'training_engagement' | 'student_batch';
  title: string;
  session: 'morning' | 'evening';
}

interface DayShiftData {
  morning: ScheduleItem[];
  evening: ScheduleItem[];
}

interface EmployeeSchedule {
  resource_id: string;
  employee_name: string;
  days: Record<string, DayShiftData>;
}


const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];

export const WeeklySchedule: React.FC = () => {
  const [schedules, setSchedules] = useState<EmployeeSchedule[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const API_BASE = import.meta.env.VITE_BACKEND_URL || 'https://employee-allocation-ai.onrender.com';
  
  useEffect(() => {
    fetchCalendarSchedule();
  }, []);

  const fetchCalendarSchedule = async () => {
    try {
      setLoading(true);
      const res = await axios.get(`${API_BASE}/api/schedule/calendar`);
      setSchedules(res.data.schedules);
    } catch (err) {
      console.error('Failed to load schedule calendar:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleShiftChange = async (
    itemId: string, 
    entityType: string, 
    newSession: 'morning' | 'evening'
  ) => {
    setUpdatingId(itemId);
    try {
      await axios.patch(`${API_BASE}/api/schedule/shift`, {
        item_id: itemId,
        entity_type: entityType,
        session: newSession,
      });

      await fetchCalendarSchedule();
    } catch (err) {
      console.error('Failed to update shift:', err);
      alert('Failed to update shift in the database.');
    } finally {
      setUpdatingId(null);
    }
  };

  const getBadgeStyle = (type: string) => {
    switch (type.toLowerCase()) {
      case 'project': 
        return { label: 'Project', color: 'bg-blue-100 text-blue-800 border-blue-200' };
      case 'training_engagement': 
        return { label: 'Training', color: 'bg-purple-100 text-purple-800 border-purple-200' };
      case 'student_batch': 
        return { label: 'Student Batch', color: 'bg-emerald-100 text-emerald-800 border-emerald-200' };
      default: 
        return { label: type, color: 'bg-gray-100 text-gray-800 border-gray-200' };
    }
  };

  if (loading) {
    return (
      <div className="p-12 text-center text-cyan-400 font-medium bg-[#050814] min-h-screen flex flex-col justify-center items-center">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400 mb-3 shadow-[0_0_15px_rgba(34,211,238,0.8)]"></div>
        <p className="text-cyan-200">Loading 5-Day Calendar Schedule...</p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-[105rem] mx-auto bg-[#050814] text-zinc-100 min-h-screen">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-extrabold bg-gradient-to-r from-cyan-400 via-fuchsia-400 to-amber-300 bg-clip-text text-transparent tracking-tight drop-shadow-[0_0_12px_rgba(34,211,238,0.3)]">
            Weekly Calendar Schedule
          </h1>
          <p className="text-sm text-indigo-300/80">Employee schedule view (Monday – Friday)</p>
        </div>
        <button
          onClick={fetchCalendarSchedule}
          className="px-4 py-2 bg-gradient-to-r from-violet-600 via-indigo-600 to-cyan-600 hover:from-violet-500 hover:to-cyan-500 text-white font-medium rounded-md text-sm transition shadow-[0_0_20px_rgba(124,58,237,0.5)] hover:shadow-[0_0_25px_rgba(34,211,238,0.6)] flex items-center gap-2"
        >
          <span>↻</span> Refresh Schedule
        </button>
      </div>

      {/* Main Calendar Matrix Table */}
      <div className="overflow-x-auto rounded-xl border border-indigo-900/60 bg-[#0a0f1d]/90 shadow-[0_0_35px_rgba(5,8,20,0.95)] backdrop-blur-sm">
        <table className="min-w-full border-collapse">
          <thead>
            <tr className="bg-[#0f172a] text-cyan-300 text-xs uppercase font-semibold border-b border-indigo-900/60">
              <th className="p-4 text-left w-52 border-r border-indigo-900/60">Employee</th>
              {DAYS.map((day) => (
                <th key={day} className="p-4 text-center border-r border-indigo-900/60 min-w-[210px] tracking-wider text-cyan-200 font-extrabold">
                  {day}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-indigo-900/40 text-sm">
            {schedules.map((emp) => (
              <tr key={emp.resource_id} className="hover:bg-indigo-950/30 transition">
                {/* Employee Column */}
                <td className="p-4 align-top border-r border-indigo-900/60 bg-[#080d1a]">
                  <div className="font-bold text-white tracking-wide">{emp.employee_name}</div>
                  
                  <div className="text-[11px] text-fuchsia-400/80 mt-2 font-mono">ID: {emp.resource_id}</div>
                </td>

                {/* Days Columns (Monday to Friday) */}
                {DAYS.map((day) => {
                  const dayData = emp.days[day] || { morning: [], evening: [] };
                  return (
                    <td key={day} className="p-3 align-top border-r border-indigo-900/40">
                      <div className="space-y-3">
                        {/* Morning Shift Block (Amber Glow) */}
                        <div className="bg-gradient-to-br from-amber-500/10 via-amber-950/20 to-transparent p-2.5 rounded-lg border border-amber-500/40 shadow-[0_0_12px_rgba(245,158,11,0.15)]">
                          <div className="text-[10px] font-bold text-amber-300 uppercase tracking-wider mb-2 flex items-center justify-between">
                            <span>Morning</span>
                            <span className="text-[9px] text-amber-400/80 font-normal">09:00 - 13:00</span>
                          </div>
                          {dayData.morning.length === 0 ? (
                            <div className="text-[11px] text-indigo-300/40 italic">No allocation</div>
                          ) : (
                            dayData.morning.map((item) => (
                              <CalendarCard
                                key={`${item.item_id}-m`}
                                item={item}
                                updatingId={updatingId}
                                getBadgeStyle={getBadgeStyle}
                                onShiftChange={handleShiftChange}
                              />
                            ))
                          )}
                        </div>

                        {/* Evening Shift Block (Indigo Glow) */}
                        <div className="bg-gradient-to-br from-indigo-500/10 via-indigo-950/20 to-transparent p-2.5 rounded-lg border border-indigo-500/40 shadow-[0_0_12px_rgba(99,102,241,0.15)]">
                          <div className="text-[10px] font-bold text-indigo-300 uppercase tracking-wider mb-2 flex items-center justify-between">
                            <span>Evening</span>
                            <span className="text-[9px] text-indigo-400/80 font-normal">14:00 - 18:00</span>
                          </div>
                          {dayData.evening.length === 0 ? (
                            <div className="text-[11px] text-indigo-300/40 italic">No allocation</div>
                          ) : (
                            dayData.evening.map((item) => (
                              <CalendarCard
                                key={`${item.item_id}-e`}
                                item={item}
                                updatingId={updatingId}
                                getBadgeStyle={getBadgeStyle}
                                onShiftChange={handleShiftChange}
                              />
                            ))
                          )}
                        </div>
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

interface CardProps {
  item: ScheduleItem;
  updatingId: string | null;
  getBadgeStyle: (type: string) => { label: string; color: string };
  onShiftChange: (id: string, entityType: string, session: 'morning' | 'evening') => void;
}

const CalendarCard: React.FC<CardProps> = ({ item, updatingId, getBadgeStyle, onShiftChange }) => {
  const isUpdating = updatingId === item.item_id;
  const badge = getBadgeStyle(item.entity_type);

  return (
    <div className={`p-2.5 bg-[#041d24] hover:bg-[#18243e] border border-indigo-800/60 hover:border-cyan-400 rounded-md shadow-md hover:shadow-[0_0_15px_rgba(34,211,238,0.25)] space-y-1.5 mb-2 transition-all ${isUpdating ? 'opacity-50' : ''}`}>
      <div className="flex items-center justify-between">
        <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border uppercase tracking-wider ${badge.color}`}>
          {badge.label}
        </span>
        
      </div>

      <div className="text-xs font-semibold text-white leading-tight">
        {item.title}
      </div>

      

      {/* Dynamic Session Switcher */}
      <div className="pt-1.5 border-t border-indigo-900/60 flex items-center justify-between">
        <span className="text-[10px] text-indigo-300 uppercase font-medium">Shift</span>
        <select
          disabled={isUpdating}
          value={item.session}
          onChange={(e) => onShiftChange(item.item_id, item.entity_type, e.target.value as 'morning' | 'evening')}
          className="text-xs border border-indigo-500/50 rounded px-1.5 py-0.5 bg-[#080d1a] text-cyan-200 focus:ring-1 focus:ring-cyan-400 focus:outline-none cursor-pointer hover:border-cyan-400 transition-all"
        >
          <option value="morning">Morning</option>
          <option value="evening">Evening</option>
        </select>
      </div>
    </div>
  );
};