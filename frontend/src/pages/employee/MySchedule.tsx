import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import api from '../../services/api';

// --- Interfaces ---
export interface ScheduleItem {
  item_id: string;
  entity_type: 'project' | 'training_engagement' | 'student_batch';
  title: string;
  session: 'morning' | 'evening';
  is_override?: boolean;
}

export interface DayShiftData {
  morning: ScheduleItem[];
  evening: ScheduleItem[];
}

export interface MyScheduleResponse {
  resource_id?: string;
  employee_name?: string;
  days: Record<string, DayShiftData>;
}

// --- Date Helpers ---
const getMonday = (d: Date): Date => {
  const date = new Date(d);
  const day = date.getDay();
  const diff = date.getDate() - day + (day === 0 ? -6 : 1); // Adjust when Sunday
  date.setDate(diff);
  return date;
};

const formatDateString = (dateObj: Date): string => {
  const yyyy = dateObj.getFullYear();
  const mm = String(dateObj.getMonth() + 1).padStart(2, '0');
  const dd = String(dateObj.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
};

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];

export const MySchedule: React.FC = () => {
  const [currentWeekStart, setCurrentWeekStart] = useState<Date>(() => getMonday(new Date()));
  const [scheduleData, setScheduleData] = useState<MyScheduleResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  // Override Modal / Configuration state
  const [selectedOverrideItem, setSelectedOverrideItem] = useState<{
    item: ScheduleItem;
    date: string;
    dayName: string;
  } | null>(null);
  const [overrideScope, setOverrideScope] = useState<'single_day' | 'full_week'>('single_day');
  const [overrideReason, setOverrideReason] = useState<string>('');

  const API_BASE = import.meta.env.VITE_BACKEND_URL || 'https://employee-allocation-ai.onrender.com';

  // --- Fetch Employee Schedule ---
  const fetchMySchedule = useCallback(async () => {
    try {
      setLoading(true);
      const weekStartStr = formatDateString(currentWeekStart);
      const res = await api.get(`${API_BASE}/api/schedule/my-schedule`, {
        params: { week_start: weekStartStr }
      });
      setScheduleData(res.data);
    } catch (err) {
      console.error('Failed to load employee schedule:', err);
    } {
      setLoading(false);
    }
  }, [currentWeekStart, API_BASE]);

  useEffect(() => {
    fetchMySchedule();
  }, [fetchMySchedule]);

  // --- Week Navigation Handlers ---
  const handlePrevWeek = () => {
    const prev = new Date(currentWeekStart);
    prev.setDate(prev.getDate() - 7);
    setCurrentWeekStart(prev);
  };

  const handleNextWeek = () => {
    const next = new Date(currentWeekStart);
    next.setDate(next.getDate() + 7);
    setCurrentWeekStart(next);
  };

  const handleCurrentWeek = () => {
    setCurrentWeekStart(getMonday(new Date()));
  };

  // --- Shift Override Handler ---
  const handleShiftChange = async (
    item: ScheduleItem,
    newSession: 'morning' | 'evening',
    overrideDate: string
  ) => {
    setUpdatingId(item.item_id);
    const weekStartStr = formatDateString(currentWeekStart);

    try {
      const payload = {
        item_id: item.item_id,
        entity_type: item.entity_type,
        new_session: newSession,
        scope: overrideScope,
        override_date: overrideScope === 'single_day' ? overrideDate : null,
        week_start_date: overrideScope === 'full_week' ? weekStartStr : null,
        reason: overrideReason || 'Shift updated via personal schedule portal',
      };

      await api.post(`${API_BASE}/api/schedule/override`, payload);
      
      // Close modal if open
      setSelectedOverrideItem(null);
      setOverrideReason('');
      
      // Refresh schedule
      await fetchMySchedule();
    } catch (err) {
      console.error('Failed to update shift override:', err);
      alert('Failed to update shift schedule.');
    } finally {
      setUpdatingId(null);
    }
  };

  const getBadgeStyle = (type: string) => {
    switch (type.toLowerCase()) {
      case 'project':
        return { label: 'Project', color: 'bg-blue-500/20 text-blue-300 border-blue-500/40' };
      case 'training_engagement':
        return { label: 'Training', color: 'bg-purple-500/20 text-purple-300 border-purple-500/40' };
      case 'student_batch':
        return { label: 'Student Batch', color: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' };
      default:
        return { label: type, color: 'bg-gray-500/20 text-gray-300 border-gray-500/40' };
    }
  };

  const formattedWeekStart = formatDateString(currentWeekStart);
  const formattedWeekEnd = formatDateString(
    new Date(currentWeekStart.getTime() + 4 * 24 * 60 * 60 * 1000)
  );

  if (loading && !scheduleData) {
    return (
      <div className="p-12 text-center text-cyan-400 font-medium bg-[#050814] min-h-screen flex flex-col justify-center items-center">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400 mb-3 shadow-[0_0_15px_rgba(34,211,238,0.8)]"></div>
        <p className="text-cyan-200">Loading Your Schedule...</p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-[105rem] mx-auto bg-[#050814] text-zinc-100 min-h-screen space-y-6">
      {/* Header Section */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-[#0a0f1d]/90 p-5 rounded-xl border border-indigo-900/60 shadow-[0_0_35px_rgba(5,8,20,0.95)] backdrop-blur-sm">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-extrabold bg-gradient-to-r from-cyan-400 via-fuchsia-400 to-amber-300 bg-clip-text text-transparent tracking-tight drop-shadow-[0_0_12px_rgba(34,211,238,0.3)]">
              My Work Schedule
            </h1>
            {scheduleData?.employee_name && (
              <span className="px-3 py-1 rounded-full text-xs font-semibold bg-cyan-950/80 text-cyan-300 border border-cyan-500/40 shadow-[0_0_10px_rgba(34,211,238,0.2)]">
                {scheduleData.employee_name}
              </span>
            )}
          </div>
          <p className="text-sm text-indigo-300/80 mt-1">
            Personal 5-day shift assignments &amp; override portal
          </p>
        </div>

        {/* Date Controls & Refresh */}
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={handleCurrentWeek}
            className="px-3 py-1.5 text-xs font-semibold bg-indigo-950/80 hover:bg-indigo-900 text-cyan-300 border border-indigo-700/60 rounded-md transition"
          >
            This Week
          </button>

          <div className="flex items-center bg-[#080d1a] rounded-lg border border-indigo-900/60 p-1">
            <button
              onClick={handlePrevWeek}
              className="p-1.5 hover:bg-indigo-900/50 rounded transition text-cyan-300"
              title="Previous Week"
            >
              &#9664;
            </button>
            <span className="px-3 text-xs font-semibold text-cyan-200 min-w-[170px] text-center font-mono">
              {formattedWeekStart} &rarr; {formattedWeekEnd}
            </span>
            <button
              onClick={handleNextWeek}
              className="p-1.5 hover:bg-indigo-900/50 rounded transition text-cyan-300"
              title="Next Week"
            >
              &#9654;
            </button>
          </div>

          <button
            onClick={fetchMySchedule}
            className="px-4 py-2 bg-gradient-to-r from-violet-600 via-indigo-600 to-cyan-600 hover:from-violet-500 hover:to-cyan-500 text-white font-medium rounded-md text-sm transition shadow-[0_0_20px_rgba(124,58,237,0.5)] hover:shadow-[0_0_25px_rgba(34,211,238,0.6)] flex items-center gap-2"
          >
            <span>↻</span> Refresh
          </button>
        </div>
      </div>

      {/* 5-Day Weekly Grid */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        {DAYS.map((day, idx) => {
          const dayDateObj = new Date(currentWeekStart);
          dayDateObj.setDate(dayDateObj.getDate() + idx);
          const dayDateStr = formatDateString(dayDateObj);
          const isToday = formatDateString(new Date()) === dayDateStr;

          const dayData = scheduleData?.days?.[day] || { morning: [], evening: [] };

          return (
            <div
              key={day}
              className={`rounded-xl border bg-[#0a0f1d]/90 shadow-[0_0_25px_rgba(5,8,20,0.8)] backdrop-blur-sm flex flex-col overflow-hidden transition-all ${
                isToday
                  ? 'border-cyan-400 ring-1 ring-cyan-400/50 shadow-[0_0_20px_rgba(34,211,238,0.25)]'
                  : 'border-indigo-900/60'
              }`}
            >
              {/* Day Header */}
              <div
                className={`p-3 text-center border-b ${
                  isToday
                    ? 'bg-gradient-to-r from-cyan-950 via-indigo-950 to-cyan-950 border-cyan-400/60 text-cyan-300'
                    : 'bg-[#0f172a] border-indigo-900/60 text-cyan-200'
                }`}
              >
                <div className="text-xs uppercase font-extrabold tracking-wider">{day}</div>
                <div className="text-sm font-semibold text-indigo-300/90 font-mono mt-0.5">
                  {dayDateStr}
                </div>
              </div>

              {/* Shifts Body */}
              <div className="p-3 space-y-4 flex-1 flex flex-col justify-between">
                {/* MORNING SHIFT BLOCK */}
                <div className="bg-gradient-to-br from-amber-500/10 via-amber-950/20 to-transparent p-2.5 rounded-lg border border-amber-500/40 shadow-[0_0_12px_rgba(245,158,11,0.15)] flex-1">
                  <div className="text-[10px] font-bold text-amber-300 uppercase tracking-wider mb-2 flex items-center justify-between">
                    <span>Morning</span>
                    <span className="text-[9px] text-amber-400/80 font-normal font-mono">09:00 - 13:00</span>
                  </div>

                  {dayData.morning.length === 0 ? (
                    <div className="text-[11px] text-indigo-300/40 italic text-center py-2">
                      No allocation
                    </div>
                  ) : (
                    dayData.morning.map((item) => (
                      <MyScheduleCard
                        key={`${item.item_id}-m`}
                        item={item}
                        dayDate={dayDateStr}
                        dayName={day}
                        updatingId={updatingId}
                        getBadgeStyle={getBadgeStyle}
                        onQuickShiftChange={(newSession) =>
                          handleShiftChange(item, newSession, dayDateStr)
                        }
                        onOpenOverrideModal={() =>
                          setSelectedOverrideItem({ item, date: dayDateStr, dayName: day })
                        }
                      />
                    ))
                  )}
                </div>

                {/* EVENING SHIFT BLOCK */}
                <div className="bg-gradient-to-br from-indigo-500/10 via-indigo-950/20 to-transparent p-2.5 rounded-lg border border-indigo-500/40 shadow-[0_0_12px_rgba(99,102,241,0.15)] flex-1">
                  <div className="text-[10px] font-bold text-indigo-300 uppercase tracking-wider mb-2 flex items-center justify-between">
                    <span>Evening</span>
                    <span className="text-[9px] text-indigo-400/80 font-normal font-mono">14:00 - 18:00</span>
                  </div>

                  {dayData.evening.length === 0 ? (
                    <div className="text-[11px] text-indigo-300/40 italic text-center py-2">
                      No allocation
                    </div>
                  ) : (
                    dayData.evening.map((item) => (
                      <MyScheduleCard
                        key={`${item.item_id}-e`}
                        item={item}
                        dayDate={dayDateStr}
                        dayName={day}
                        updatingId={updatingId}
                        getBadgeStyle={getBadgeStyle}
                        onQuickShiftChange={(newSession) =>
                          handleShiftChange(item, newSession, dayDateStr)
                        }
                        onOpenOverrideModal={() =>
                          setSelectedOverrideItem({ item, date: dayDateStr, dayName: day })
                        }
                      />
                    ))
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Advanced Override Modal */}
      {selectedOverrideItem && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-[#0a0f1d] border border-cyan-500/50 rounded-xl max-w-md w-full p-6 shadow-[0_0_50px_rgba(34,211,238,0.25)] space-y-4">
            <div className="flex justify-between items-center border-b border-indigo-900/60 pb-3">
              <h3 className="text-lg font-bold text-cyan-300">Shift Override Options</h3>
              <button
                onClick={() => setSelectedOverrideItem(null)}
                className="text-indigo-400 hover:text-white transition"
              >
                ✕
              </button>
            </div>

            <div className="p-3 bg-[#041d24] rounded-lg border border-indigo-800/60 space-y-1">
              <div className="text-xs text-indigo-300">Assignment:</div>
              <div className="text-sm font-bold text-white">{selectedOverrideItem.item.title}</div>
              <div className="text-xs text-cyan-400/90 font-mono">
                {selectedOverrideItem.dayName} ({selectedOverrideItem.date})
              </div>
            </div>

            {/* Scope Selection */}
            <div className="space-y-1.5">
              <label className="text-xs text-indigo-300 uppercase font-semibold">
                Apply Override Scope
              </label>
              <select
                value={overrideScope}
                onChange={(e) => setOverrideScope(e.target.value as 'single_day' | 'full_week')}
                className="w-full text-xs bg-[#080d1a] border border-indigo-500/50 rounded-lg p-2 text-cyan-200 focus:ring-1 focus:ring-cyan-400 focus:outline-none"
              >
                <option value="single_day">Single Day ({selectedOverrideItem.date})</option>
                <option value="full_week">Full Week (Entire Mon-Fri)</option>
              </select>
            </div>

            {/* Reason input */}
            <div className="space-y-1.5">
              <label className="text-xs text-indigo-300 uppercase font-semibold">
                Reason / Note <span className="text-indigo-500 font-normal">(Optional)</span>
              </label>
              <input
                type="text"
                placeholder="e.g. Personal schedule adjustment"
                value={overrideReason}
                onChange={(e) => setOverrideReason(e.target.value)}
                className="w-full text-xs bg-[#080d1a] border border-indigo-500/50 rounded-lg p-2 text-cyan-200 focus:ring-1 focus:ring-cyan-400 focus:outline-none"
              />
            </div>

            {/* Action Buttons */}
            <div className="flex justify-end gap-3 pt-3 border-t border-indigo-900/60">
              <button
                onClick={() => setSelectedOverrideItem(null)}
                className="px-4 py-2 text-xs font-semibold text-indigo-300 hover:text-white transition"
              >
                Cancel
              </button>
              <button
                onClick={() =>
                  handleShiftChange(
                    selectedOverrideItem.item,
                    selectedOverrideItem.item.session === 'morning' ? 'evening' : 'morning',
                    selectedOverrideItem.date
                  )
                }
                className="px-4 py-2 bg-gradient-to-r from-violet-600 to-cyan-600 hover:from-violet-500 hover:to-cyan-500 text-white font-semibold text-xs rounded-lg transition shadow-[0_0_15px_rgba(34,211,238,0.4)]"
              >
                Confirm Shift Switch
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// --- Schedule Card Component ---
interface MyScheduleCardProps {
  item: ScheduleItem;
  dayDate: string;
  dayName: string;
  updatingId: string | null;
  getBadgeStyle: (type: string) => { label: string; color: string };
  onQuickShiftChange: (newSession: 'morning' | 'evening') => void;
  onOpenOverrideModal: () => void;
}

const MyScheduleCard: React.FC<MyScheduleCardProps> = ({
  item,
  updatingId,
  getBadgeStyle,
  onQuickShiftChange,
  onOpenOverrideModal,
}) => {
  const isUpdating = updatingId === item.item_id;
  const badge = getBadgeStyle(item.entity_type);

  return (
    <div
      className={`p-2.5 bg-[#041d24] hover:bg-[#18243e] border border-indigo-800/60 hover:border-cyan-400 rounded-md shadow-md hover:shadow-[0_0_15px_rgba(34,211,238,0.25)] space-y-2 mb-2 transition-all ${
        isUpdating ? 'opacity-50 pointer-events-none' : ''
      }`}
    >
      <div className="flex items-center justify-between">
        <span
          className={`text-[9px] font-bold px-1.5 py-0.5 rounded border uppercase tracking-wider ${badge.color}`}
        >
          {badge.label}
        </span>
        {item.is_override && (
          <span className="text-[9px] bg-amber-500/20 text-amber-300 border border-amber-500/40 px-1 py-0.5 rounded font-mono">
            Shifted
          </span>
        )}
      </div>

      <div className="text-xs font-semibold text-white leading-tight">{item.title}</div>

      {/* Session Switcher & Config Button */}
      <div className="pt-1.5 border-t border-indigo-900/60 flex items-center justify-between gap-1">
        <select
          disabled={isUpdating}
          value={item.session}
          onChange={(e) => onQuickShiftChange(e.target.value as 'morning' | 'evening')}
          className="text-[11px] border border-indigo-500/50 rounded px-1.5 py-0.5 bg-[#080d1a] text-cyan-200 focus:ring-1 focus:ring-cyan-400 focus:outline-none cursor-pointer hover:border-cyan-400 transition-all"
        >
          <option value="morning">Morning</option>
          <option value="evening">Evening</option>
        </select>

        <button
          onClick={onOpenOverrideModal}
          className="text-[10px] text-fuchsia-300 hover:text-fuchsia-100 bg-fuchsia-950/60 hover:bg-fuchsia-900 border border-fuchsia-700/50 px-1.5 py-0.5 rounded transition"
          title="Advanced override settings"
        >
          Options ⚙
        </button>
      </div>
    </div>
  );
};