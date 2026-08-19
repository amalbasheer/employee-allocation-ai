import React, { useState, useEffect } from 'react';
import { Card } from '../../components/common/Card';
import { 
  Clock, 
  Calendar, 
  Briefcase, 
  Palmtree, 
  Save, 
  Plus, 
  CheckCircle2, 
  AlertCircle,
  TrendingDown,
  ChevronRight
} from 'lucide-react';

// Data Contracts matching FastAPI backend schemas
interface DailyBandwidth {
  today: string;
  day_of_week: string;
  gross_weekly_hours: number;
  elapsed_hours_this_week: number;
  assigned_project_hours: number;
  remaining_unallocated_hours: number;
}

interface WeeklyBandwidth {
  week_start_date: string;
  gross_available_hours: number;
  allocated_hours: number;
  net_free_hours: number;
  is_on_leave: boolean;
}

export const EmployeeAvailabilityPage: React.FC<{ employeeId?: string }> = ({ 
  employeeId = 'rp2-emp-0001' 
}) => {
  // State for metrics & list projections
  const [dailyData, setDailyData] = useState<DailyBandwidth | null>(null);
  const [weeklyProjections, setWeeklyProjections] = useState<WeeklyBandwidth[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Form State: Single-Week Upsert
  const [singleWeekDate, setSingleWeekDate] = useState<string>('');
  const [singleWeekHours, setSingleWeekHours] = useState<number>(40);
  const [singleWeekIsLeave, setSingleWeekIsLeave] = useState<boolean>(false);

  // Form State: Multi-Week Leave
  const [leaveStartDate, setLeaveStartDate] = useState<string>('');
  const [leaveEndDate, setLeaveEndDate] = useState<string>('');
  const [leaveReason, setLeaveReason] = useState<string>('');

  // Fetch initial data from APIs
  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      // 1. Fetch Daily Remaining Bandwidth
      const dailyRes = await fetch(`/api/employees/${employeeId}/daily-bandwidth`);
      if (dailyRes.ok) {
        const dData = await dailyRes.json();
        setDailyData(dData);
      }

      // 2. Fetch 8-Week Bandwidth Projection
      const weeklyRes = await fetch(`/api/employees/${employeeId}/bandwidth?num_weeks=8`);
      if (weeklyRes.ok) {
        const wData = await weeklyRes.json();
        setWeeklyProjections(wData);
      }
    } catch (err) {
      console.error('Failed to load availability data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, [employeeId]);

  // Handler: Update Single Week
  const handleSingleWeekSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!singleWeekDate) return;

    try {
      const res = await fetch(`/api/employees/${employeeId}/availability`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          week_start_date: singleWeekDate,
          available_hours: singleWeekIsLeave ? 0 : singleWeekHours,
          is_on_leave: singleWeekIsLeave,
        }),
      });

      if (res.ok) {
        setStatusMessage({ type: 'success', text: 'Weekly availability updated successfully!' });
        fetchDashboardData();
      } else {
        throw new Error('Failed to update availability');
      }
    } catch (err) {
      setStatusMessage({ type: 'error', text: 'Error updating availability record.' });
    }
  };

  // Handler: Submit Multi-Week PTO Leave
  const handleLeaveSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!leaveStartDate || !leaveEndDate) return;

    try {
      const res = await fetch(`/api/employees/${employeeId}/leave`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          start_date: leaveStartDate,
          end_date: leaveEndDate,
          reason: leaveReason,
        }),
      });

      if (res.ok) {
        setStatusMessage({ type: 'success', text: 'Leave request submitted across selected dates!' });
        setLeaveStartDate('');
        setLeaveEndDate('');
        setLeaveReason('');
        fetchDashboardData();
      } else {
        throw new Error('Failed to submit leave');
      }
    } catch (err) {
      setStatusMessage({ type: 'error', text: 'Error submitting leave request.' });
    }
  };

  const metrics = [
    {
      label: 'Free Hours Left This Week',
      value: dailyData ? `${dailyData.remaining_unallocated_hours} hrs` : '--',
      icon: Clock,
      color: 'text-emerald-400',
      subtext: dailyData ? `For ${dailyData.day_of_week}` : '',
    },
    {
      label: 'Allocated Project Hours',
      value: dailyData ? `${dailyData.assigned_project_hours} hrs` : '--',
      icon: Briefcase,
      color: 'text-indigo-400',
      subtext: 'Active commitments',
    },
    {
      label: 'Elapsed Working Hours',
      value: dailyData ? `${dailyData.elapsed_hours_this_week} hrs` : '--',
      icon: TrendingDown,
      color: 'text-amber-400',
      subtext: 'Past days in week',
    },
    {
      label: 'Gross Weekly Capacity',
      value: dailyData ? `${dailyData.gross_weekly_hours} hrs` : '40 hrs',
      icon: Calendar,
      color: 'text-rose-400',
      subtext: 'Standard capacity',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">My Availability & Bandwidth</h1>
        <p className="text-slate-400 text-sm">
          Track remaining unallocated hours, update weekly capacity, and schedule leave.
        </p>
      </div>

      {/* Notification Banner */}
      {statusMessage && (
        <div
          className={`p-4 rounded-xl border flex items-center justify-between ${
            statusMessage.type === 'success'
              ? 'bg-emerald-950/40 border-emerald-800 text-emerald-300'
              : 'bg-rose-950/40 border-rose-800 text-rose-300'
          }`}
        >
          <div className="flex items-center gap-2 text-sm font-medium">
            {statusMessage.type === 'success' ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            ) : (
              <AlertCircle className="w-5 h-5 text-rose-400" />
            )}
            {statusMessage.text}
          </div>
          <button
            onClick={() => setStatusMessage(null)}
            className="text-xs opacity-70 hover:opacity-100"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Top Key Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {metrics.map((m, i) => {
          const Icon = m.icon;
          return (
            <Card key={i}>
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-xs text-slate-400">{m.label}</span>
                  <h3 className="text-2xl font-black text-white mt-1">{m.value}</h3>
                  <span className="text-[11px] text-slate-500">{m.subtext}</span>
                </div>
                <div className={`p-3 bg-slate-950 rounded-xl border border-slate-800 ${m.color}`}>
                  <Icon className="w-6 h-6" />
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      {/* Current Week Breakdown Progress Bar */}
      {dailyData && (
        <Card>
          <div className="space-y-3">
            <div className="flex justify-between items-center text-sm">
              <span className="font-semibold text-white">This Week's Capacity Utilization</span>
              <span className="text-slate-400 text-xs">
                {dailyData.remaining_unallocated_hours} hrs available of {dailyData.gross_weekly_hours} hrs
              </span>
            </div>

            {/* Segmented Capacity Progress Bar */}
            <div className="w-full bg-slate-950 border border-slate-800 h-4 rounded-lg overflow-hidden flex">
              {/* Allocated Hours Segment */}
              <div
                style={{
                  width: `${(dailyData.assigned_project_hours / dailyData.gross_weekly_hours) * 100}%`,
                }}
                className="bg-indigo-500 h-full transition-all"
                title={`Allocated: ${dailyData.assigned_project_hours} hrs`}
              />
              {/* Elapsed Time Segment */}
              <div
                style={{
                  width: `${(dailyData.elapsed_hours_this_week / dailyData.gross_weekly_hours) * 100}%`,
                }}
                className="bg-amber-500/60 h-full transition-all"
                title={`Elapsed Time: ${dailyData.elapsed_hours_this_week} hrs`}
              />
              {/* Remaining Free Capacity Segment */}
              <div
                style={{
                  width: `${(dailyData.remaining_unallocated_hours / dailyData.gross_weekly_hours) * 100}%`,
                }}
                className="bg-emerald-500 h-full transition-all"
                title={`Free Bandwidth: ${dailyData.remaining_unallocated_hours} hrs`}
              />
            </div>

            {/* Legend */}
            <div className="flex items-center gap-6 text-xs text-slate-400 pt-1">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-sm bg-indigo-500 inline-block" />
                Allocated ({dailyData.assigned_project_hours}h)
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-sm bg-amber-500/60 inline-block" />
                Elapsed ({dailyData.elapsed_hours_this_week}h)
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-sm bg-emerald-500 inline-block" />
                Remaining Free ({dailyData.remaining_unallocated_hours}h)
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Main Grid: Management Forms & Timeline Projection */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column: Action Forms (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          
          {/* Form 1: Single Week Adjustment */}
          <Card>
            <div className="flex items-center gap-2 mb-4">
              <Clock className="w-5 h-5 text-indigo-400" />
              <h2 className="text-lg font-bold text-white">Update Weekly Hours</h2>
            </div>

            <form onSubmit={handleSingleWeekSubmit} className="space-y-4">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Week Start Date (Monday)</label>
                <input
                  type="date"
                  value={singleWeekDate}
                  onChange={(e) => setSingleWeekDate(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs text-slate-400 mb-1">Available Hours</label>
                <input
                  type="number"
                  min="0"
                  max="80"
                  value={singleWeekHours}
                  disabled={singleWeekIsLeave}
                  onChange={(e) => setSingleWeekHours(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500 disabled:opacity-40"
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="isLeaveToggle"
                  checked={singleWeekIsLeave}
                  onChange={(e) => setSingleWeekIsLeave(e.target.checked)}
                  className="w-4 h-4 rounded bg-slate-950 border-slate-800 text-indigo-500 focus:ring-0"
                />
                <label htmlFor="isLeaveToggle" className="text-xs text-slate-300">
                  Mark as On Leave / PTO for this week
                </label>
              </div>

              <button
                type="submit"
                className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm rounded-xl py-2.5 flex items-center justify-center gap-2 transition-colors"
              >
                <Save className="w-4 h-4" />
                Save Availability
              </button>
            </form>
          </Card>

          {/* Form 2: Date Range PTO Leave */}
          <Card>
            <div className="flex items-center gap-2 mb-4">
              <Palmtree className="w-5 h-5 text-rose-400" />
              <h2 className="text-lg font-bold text-white">Book Vacation / PTO</h2>
            </div>

            <form onSubmit={handleLeaveSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Start Date</label>
                  <input
                    type="date"
                    value={leaveStartDate}
                    onChange={(e) => setLeaveStartDate(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">End Date</label>
                  <input
                    type="date"
                    value={leaveEndDate}
                    onChange={(e) => setLeaveEndDate(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs text-slate-400 mb-1">Reason / Notes (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g., Annual Vacation"
                  value={leaveReason}
                  onChange={(e) => setLeaveReason(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>

              <button
                type="submit"
                className="w-full bg-slate-800 hover:bg-slate-700 border border-slate-700 text-white font-medium text-sm rounded-xl py-2.5 flex items-center justify-center gap-2 transition-colors"
              >
                <Plus className="w-4 h-4 text-rose-400" />
                Submit Multi-Week Leave
              </button>
            </form>
          </Card>
        </div>

        {/* Right Column: 8-Week Bandwidth Forecast (7 cols) */}
        <div className="lg:col-span-7">
          <Card>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-lg font-bold text-white">8-Week Bandwidth Forecast</h2>
                <p className="text-xs text-slate-400">Projected net free hours across upcoming weeks</p>
              </div>
              <span className="text-xs text-indigo-400 bg-indigo-950/60 border border-indigo-800/50 px-2.5 py-1 rounded-lg">
                Upcoming Schedule
              </span>
            </div>

            {loading ? (
              <div className="py-12 text-center text-slate-500 text-sm">
                Loading capacity forecast...
              </div>
            ) : weeklyProjections.length === 0 ? (
              <div className="py-12 text-center text-slate-500 text-sm">
                No future capacity records found.
              </div>
            ) : (
              <div className="space-y-3">
                {weeklyProjections.map((item, index) => (
                  <div
                    key={index}
                    className="p-3 bg-slate-950 rounded-xl border border-slate-800/80 flex items-center justify-between hover:border-slate-700 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-slate-900 rounded-lg text-slate-400">
                        <Calendar className="w-4 h-4 text-indigo-400" />
                      </div>
                      <div>
                        <div className="text-sm font-semibold text-white">
                          Week of {item.week_start_date}
                        </div>
                        <div className="text-xs text-slate-400 flex items-center gap-2 mt-0.5">
                          <span>Gross: {item.gross_available_hours}h</span>
                          <span>•</span>
                          <span>Allocated: {item.allocated_hours}h</span>
                        </div>
                      </div>
                    </div>

                    <div className="text-right">
                      {item.is_on_leave ? (
                        <span className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-rose-950/60 border border-rose-800 text-rose-400">
                          On Leave
                        </span>
                      ) : (
                        <div>
                          <div className="text-sm font-bold text-emerald-400">
                            {item.net_free_hours} hrs free
                          </div>
                          <div className="text-[10px] text-slate-500">Net Bandwidth</div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

      </div>
    </div>
  );
};