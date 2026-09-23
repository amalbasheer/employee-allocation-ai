import React, { useState, useEffect } from 'react';
import axios from 'axios';
import api from '../../services/api'

interface ScheduleItem {
  item_id: string;
  entity_type: 'project' | 'training_engagement' | 'student_batch';
  title: string;
  session: 'morning' | 'evening';
  is_overridden?: boolean;
  reason?: string;
  status?: string;
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

// Interface for pending shift requests needing admin approval
interface PendingShiftRequest {
  override_id: string;
  entity_type: string;
  entity_id: string;
  project_title?: string;
  batch_name?: string;
  scope: 'single_day' | 'full_week';
  override_date?: string;
  week_start_date?: string;
  original_session?: string;
  new_session: string;
  reason?: string;
  created_by_user_id?: string;
  employee_name?: string;
  created_by_role?: string;
  status: string;
}

const getFormattedDateForDay = (dayName: string): string => {
  const dayIndexMap: Record<string, number> = {
    Monday: 1,
    Tuesday: 2,
    Wednesday: 3,
    Thursday: 4,
    Friday: 5,
  };
  const targetIndex = dayIndexMap[dayName] || 1;

  const now = new Date();
  const currentDayOfWeek = now.getDay(); // 0 is Sunday, 1 is Monday...
  const distanceToMonday = currentDayOfWeek === 0 ? -6 : 1 - currentDayOfWeek;

  const monday = new Date(now);
  monday.setDate(now.getDate() + distanceToMonday);

  const targetDate = new Date(monday);
  targetDate.setDate(monday.getDate() + (targetIndex - 1));

  return targetDate.toISOString().split('T')[0];
};

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

export const WeeklySchedule: React.FC = () => {
  const [schedules, setSchedules] = useState<EmployeeSchedule[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const [currentWeekStart, setCurrentWeekStart] = useState<Date>(() => getMonday(new Date()));
    
  const [pendingRequests, setPendingRequests] = useState<PendingShiftRequest[]>([]);
  const [processingOverrideId, setProcessingOverrideId] = useState<string | null>(null);

  const API_BASE = import.meta.env.VITE_BACKEND_URL || 'https://employee-allocation-ai.onrender.com';
  
  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    setLoading(true);
    await Promise.all([fetchCalendarSchedule(), fetchPendingRequests()]);
    setLoading(false);
  };

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

  /**
   * Fetch pending shift requests for admin review
   */
  const fetchPendingRequests = async () => {
    try {
      const res = await api.get(`${API_BASE}/api/schedule/pending`);
      setPendingRequests(res.data || []);
    } catch (err) {
      console.error('Failed to load pending shift requests:', err);
    }
  };

  /**
   * Approve or Reject a pending shift request
   */
  const handleReviewRequest = async (overrideId: string, action: 'approve' | 'reject') => {
    setProcessingOverrideId(overrideId);
    try {
      await api.post(`${API_BASE}/api/schedule/review/${overrideId}`, {
        action,
      });
      // Refresh schedule and pending queue after approval/rejection
      await Promise.all([fetchCalendarSchedule(), fetchPendingRequests()]);
    } catch (err) {
      console.error(`Failed to ${action} shift request:`, err);
      alert(`Failed to ${action} shift request.`);
    } finally {
      setProcessingOverrideId(null);
    }
  };

  /**
   * Post schedule override directly (Admin direct shift change)
   */
  const handleShiftChange = async (
    itemId: string,
    entityType: 'project' | 'training_engagement' | 'student_batch',
    newSession: 'morning' | 'evening',
    scope: 'single_day' | 'full_week' = 'single_day',
    overrideDate?: string,
    weekStartDate?: string,
    reason?: string,
    status?: string
  ) => {
    setUpdatingId(itemId);
    try {
      const payload = {
        item_id: itemId,
        entity_type: entityType,
        new_session: newSession,
        scope: scope,
        override_date: scope === 'single_day' ? overrideDate : null,
        week_start_date: scope === 'full_week' ? weekStartDate : null,
        reason: reason || 'Shift changed via schedule portal',
        status: 'shifted'
      };

      await api.post(`${API_BASE}/api/schedule/override`, payload);
      await fetchCalendarSchedule();
    } catch (err) {
      console.error('Failed to update shift override:', err);
      alert('Failed to update temporary shift schedule.');
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

  const formattedWeekStart = formatDateString(currentWeekStart);
  const weekEndObj = new Date(currentWeekStart);
  weekEndObj.setDate(weekEndObj.getDate() + 4);
  const formattedWeekEnd = formatDateString(weekEndObj);


if (loading) {
    return (
      <div className="p-12 text-center text-cyan-400 font-medium bg-[#050814] min-h-screen flex flex-col justify-center items-center">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400 mb-3 shadow-[0_0_15px_rgba(34,211,238,0.8)]"></div>
        <p className="text-cyan-200">Loading 5-Day Calendar Schedule...</p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-[105rem] mx-auto bg-[#050814] text-zinc-100 min-h-screen space-y-6">
  {/* Header */}
  <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-[#0a0f1d]/90 p-5 rounded-xl border border-indigo-900/60 shadow-[0_0_35px_rgba(5,8,20,0.95)] backdrop-blur-sm">
    {/* Title Section */}
    <div>
      <h1 className="text-2xl font-extrabold bg-gradient-to-r from-cyan-400 via-fuchsia-400 to-amber-300 bg-clip-text text-transparent tracking-tight drop-shadow-[0_0_12px_rgba(34,211,238,0.3)]">
        Weekly Calendar Schedule
      </h1>
      <p className="text-sm text-indigo-300/80 mt-1">
        Employee schedule view (Monday – Friday)
      </p>
    </div>

    {/* Combined Date Controls & Refresh Button */}
    <div className="flex flex-wrap items-center gap-3">
      {/* "This Week" Button */}
      <button
        onClick={handleCurrentWeek}
        className="px-3 py-1.5 text-xs font-semibold bg-indigo-950/80 hover:bg-indigo-900 text-cyan-300 border border-indigo-700/60 rounded-md transition"
      >
        This Week
      </button>

      {/* Date Selector */}
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

      {/* Refresh Schedule Button */}
      <button
        onClick={loadAllData}
        className="px-4 py-2 bg-gradient-to-r from-violet-600 via-indigo-600 to-cyan-600 hover:from-violet-500 hover:to-cyan-500 text-white font-medium rounded-md text-sm transition shadow-[0_0_20px_rgba(124,58,237,0.5)] hover:shadow-[0_0_25px_rgba(34,211,238,0.6)] flex items-center gap-2"
      >
        <span>↻</span> Refresh Schedule
      </button>
    </div></div>

      {/* Pending Shift Requests Panel (Dark Glow Styling) */}
      {pendingRequests.length > 0 && (
        <div className="mb-6 rounded-xl border border-amber-500/40 bg-[#0a0f1d]/90 p-5 shadow-[0_0_25px_rgba(245,158,11,0.15)] backdrop-blur-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2.5">
              <span className="flex h-3 w-3 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-amber-500"></span>
              </span>
              <h2 className="text-lg font-bold text-amber-300 tracking-wide">
                Pending Shift Change Requests ({pendingRequests.length})
              </h2>
            </div>
            <span className="text-xs px-2.5 py-1 rounded bg-amber-500/10 border border-amber-500/30 text-amber-400 font-mono">
              Requires Admin Approval
            </span>
          </div>

          <div className="space-y-3">
            {pendingRequests.map((req) => {
              const badge = getBadgeStyle(req.entity_type);
              const isProcessing = processingOverrideId === req.override_id;

              return (
                <div
                  key={req.override_id}
                  className="bg-[#080d1a] border border-indigo-900/60 hover:border-amber-500/50 rounded-lg p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 transition shadow-md"
                >
                  <div className="space-y-1.5">
                    <div className="flex items-center space-x-2">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase tracking-wider ${badge.color}`}>
                        {badge.label}
                      </span>
                      {/* Entity Title/Batch Name (with fallback to ID) */}
      <span className="font-semibold text-white text-sm">
        {req.project_title || req.batch_name || req.project_title || `ID: ${req.entity_id}`}
      </span>

      {/* Optional raw ID display for quick reference */}
      {(req.batch_name || req.project_title) && (
        <span className="text-xs text-indigo-300/60 font-mono">
          ({req.entity_id})
        </span>
      )}
                      <span className="text-xs text-indigo-300/70 font-mono">
                        ({req.scope === 'single_day' ? req.override_date : `Week of ${req.week_start_date}`})
                      </span>
                    </div>
                    {/* Requested By Employee Name */}
    <div className="text-xs text-indigo-200/80">
      Requested by:{' '}
      <span className="font-semibold text-white">
        {req.employee_name || 'Unknown'}
      </span>
      {req.created_by_user_id && (
        <span className="text-indigo-300/60 text-[11px] ml-1.5 font-mono">
          ({req.created_by_user_id})
        </span>
      )}
    </div>

                    <div className="text-sm text-zinc-300">
                      Requested Shift:{' '}
                      <span className="font-semibold text-indigo-300 capitalize">
                        {req.original_session || 'Default'}
                      </span>{' '}
                      <span className="text-amber-400 font-bold">➔</span>{' '}
                      <span className="font-bold text-amber-300 capitalize">
                        {req.new_session}
                      </span>
                    </div>

                    {req.reason && (
                      <p className="text-xs text-indigo-200/60 italic">"{req.reason}"</p>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex items-center space-x-2.5 shrink-0">
                    <button
                      disabled={isProcessing}
                      onClick={() => handleReviewRequest(req.override_id, 'approve')}
                      className="px-4 py-1.5 text-xs font-semibold bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded transition shadow-[0_0_12px_rgba(16,185,129,0.3)] disabled:opacity-50"
                    >
                      {isProcessing ? 'Processing...' : 'Approve'}
                    </button>
                    <button
                      disabled={isProcessing}
                      onClick={() => handleReviewRequest(req.override_id, 'reject')}
                      className="px-4 py-1.5 text-xs font-semibold bg-gradient-to-r from-rose-600 to-red-600 hover:from-rose-500 hover:to-red-500 text-white rounded transition shadow-[0_0_12px_rgba(244,63,94,0.3)] disabled:opacity-50"
                    >
                      Reject
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

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
                  const dayDate = getFormattedDateForDay(day);
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
                                onShiftChange={(id, entityType, newSession) =>
                                  handleShiftChange(
                                    id,
                                    entityType as any,
                                    newSession,
                                    'single_day',
                                    dayDate
                                  )
                                }
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
                                onShiftChange={(id, entityType, newSession) =>
                                  handleShiftChange(
                                    id,
                                    entityType as any,
                                    newSession,
                                    'single_day',
                                    dayDate
                                  )
                                }
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
  const shiftReason = item.reason;

  return (
    <div className={`p-2.5 bg-[#041d24] hover:bg-[#18243e] border border-indigo-800/60 hover:border-cyan-400 rounded-md shadow-md hover:shadow-[0_0_15px_rgba(34,211,238,0.25)] space-y-1.5 mb-2 transition-all ${isUpdating ? 'opacity-50' : ''}`}>
      <div className="flex items-center justify-between">
        <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border uppercase tracking-wider ${badge.color}`}>
          {badge.label}
        </span>
        {item.is_overridden && (
          <span
            title={shiftReason ? `Reason: ${shiftReason}` : 'Shifted from default session'}
            className="text-[9px] bg-amber-500/20 text-amber-300 border border-amber-500/40 px-1.5 py-0.5 rounded font-mono flex items-center gap-1 cursor-help shrink-0"
          >
            <span>Shifted</span>
          </span>
        )}
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