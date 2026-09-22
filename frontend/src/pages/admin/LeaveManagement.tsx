import React, { useState, useEffect } from 'react';
import {
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  Calendar,
  Search,
  Filter,
  User,
  Check,
  X,
  RefreshCw,
  FileText
} from 'lucide-react';
import axios from 'axios';

interface LeaveRequestItem {
  request_id: string;
  employee_id: string;
  employee_name: string;
  employee_role?: string;
  start_date: string;
  end_date: string;
  leave_type: 'regular' | 'urgent';
  session?: string;
  reason?: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  created_at?: string;
  reviewed_by?: string;
  reviewed_at?: string;
}

export const LeaveManagement: React.FC = () => {
  const [leaveRequests, setLeaveRequests] = useState<LeaveRequestItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [filterStatus, setFilterStatus] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [actionFeedback, setActionFeedback] = useState<{
    type: 'success' | 'error';
    text: string;
  } | null>(null);

  // Current logged in admin ID
  const currentAdminId = 'admin-001';
  const API_BASE = import.meta.env.VITE_BACKEND_URL || 'https://employee-allocation-ai.onrender.com';
  

  // Fetch Leave Requests from Backend
  const fetchLeaveRequests = async () => {
    setLoading(true);
    try {
      const queryParam = filterStatus !== 'ALL' ? `?status=${filterStatus}` : '';
      const response = await axios.get(`${API_BASE}/api/leave/leave-requests`);
      setLeaveRequests(response.data);
    } catch (err: any) {
      console.error(err);
      // Fallback Mock Data for preview if API is down
      setLeaveRequests([
        {
          request_id: 'req-0001',
          employee_id: 'EMP-102',
          employee_name: 'Sarah Connor',
          employee_role: 'Senior Frontend Engineer',
          start_date: '2026-10-01',
          end_date: '2026-10-05',
          leave_type: 'regular',
          session: 'full_day',
          reason: 'Annual family vacation',
          status: 'PENDING',
        },
        {
          request_id: 'req-0002',
          employee_id: 'EMP-108',
          employee_name: 'John Doe',
          employee_role: 'Backend Specialist',
          start_date: '2026-09-22',
          end_date: '2026-09-24',
          leave_type: 'urgent',
          session: 'full_day',
          reason: 'Medical emergency',
          status: 'PENDING',
        },
        {
          request_id: 'req-0000',
          employee_id: 'EMP-105',
          employee_name: 'Alice Smith',
          employee_role: 'UI/UX Designer',
          start_date: '2026-09-15',
          end_date: '2026-09-18',
          leave_type: 'regular',
          session: 'full_day',
          reason: 'Personal leave',
          status: 'APPROVED',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeaveRequests();
  }, [filterStatus]);

  const handleReview = async (
  requestId: string,
  newStatus: 'APPROVED' | 'REJECTED'
) => {
  setProcessingId(requestId);
  setActionFeedback(null);

  try {
    const response = await fetch(`${API_BASE}/api/leave/leave-requests/${requestId}/review`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        // Include bearer token if authentication is handled via headers/tokens
        // 'Authorization': `Bearer ${authToken}`,
      },
      body: JSON.stringify({
        status: newStatus,
      }),
    });

    const resData = await response.json();

    if (!response.ok) {
      throw new Error(resData.detail || 'Failed to update leave request status.');
    }

    setActionFeedback({
      type: 'success',
      text: `Request ${requestId} successfully ${newStatus.toLowerCase()}! ${
        resData.projects_marked_on_leave
          ? `(${resData.projects_marked_on_leave} projects updated)`
          : ''
      }`,
    });

    // Optimistic update local state
    setLeaveRequests((prev) =>
      prev.map((item) =>
        item.request_id === requestId ? { ...item, status: newStatus } : item
      )
    );
  } catch (err: any) {
    setActionFeedback({
      type: 'error',
      text: err.message || 'An error occurred while processing.',
    });
  } finally {
    setProcessingId(null);
  }
};
  // Filtered list by search term
  const filteredRequests = leaveRequests.filter(
    (req) =>
      req.employee_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      req.employee_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      req.request_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (req.reason && req.reason.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  // Summary Metrics
  const pendingCount = leaveRequests.filter((r) => r.status === 'PENDING').length;
  const approvedCount = leaveRequests.filter((r) => r.status === 'APPROVED').length;
  const urgentCount = leaveRequests.filter((r) => r.leave_type === 'urgent').length;

  return (
    <div className="space-y-6 p-6 bg-slate-950 text-slate-100 min-h-screen">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Leave Request Approval Portal</h1>
          <p className="text-slate-400 text-sm mt-1">
            Review, approve, or reject employee PTO and urgent leave requests.
          </p>
        </div>
        <button
          onClick={fetchLeaveRequests}
          className="flex items-center gap-2 bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 px-4 py-2 rounded-xl text-sm transition-colors w-fit"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh List
        </button>
      </div>

      {/* Action Feedback Banner */}
      {actionFeedback && (
        <div
          className={`p-4 rounded-xl border flex items-center justify-between ${
            actionFeedback.type === 'success'
              ? 'bg-emerald-950/40 border-emerald-800 text-emerald-300'
              : 'bg-rose-950/40 border-rose-800 text-rose-300'
          }`}
        >
          <div className="flex items-center gap-2 text-sm font-medium">
            {actionFeedback.type === 'success' ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
            ) : (
              <XCircle className="w-5 h-5 text-rose-400 flex-shrink-0" />
            )}
            <span>{actionFeedback.text}</span>
          </div>
          <button
            onClick={() => setActionFeedback(null)}
            className="text-xs opacity-70 hover:opacity-100 text-slate-400"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-slate-900/80 border border-slate-800/80 p-4 rounded-2xl flex items-center justify-between">
          <div>
            <span className="text-xs text-slate-400 font-medium">Pending Approvals</span>
            <h3 className="text-2xl font-black text-amber-400 mt-1">{pendingCount}</h3>
            <span className="text-[11px] text-slate-500">Requires Action</span>
          </div>
          <div className="p-3 bg-amber-950/50 border border-amber-800/50 rounded-xl text-amber-400">
            <Clock className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800/80 p-4 rounded-2xl flex items-center justify-between">
          <div>
            <span className="text-xs text-slate-400 font-medium">Urgent Requests</span>
            <h3 className="text-2xl font-black text-rose-400 mt-1">{urgentCount}</h3>
            <span className="text-[11px] text-slate-500">Auto-marks projects on leave</span>
          </div>
          <div className="p-3 bg-rose-950/50 border border-rose-800/50 rounded-xl text-rose-400">
            <AlertTriangle className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800/80 p-4 rounded-2xl flex items-center justify-between">
          <div>
            <span className="text-xs text-slate-400 font-medium">Total Approved</span>
            <h3 className="text-2xl font-black text-emerald-400 mt-1">{approvedCount}</h3>
            <span className="text-[11px] text-slate-500">Capacity adjusted</span>
          </div>
          <div className="p-3 bg-emerald-950/50 border border-emerald-800/50 rounded-xl text-emerald-400">
            <CheckCircle2 className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Search & Status Filter Bar */}
      <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-2xl flex flex-col md:flex-row gap-4 justify-between items-center">
        {/* Search Input */}
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
          <input
            type="text"
            placeholder="Search employee, ID, reason..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-10 pr-4 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 placeholder-slate-500"
          />
        </div>

        {/* Filter Buttons */}
        <div className="flex items-center gap-2 w-full md:w-auto overflow-x-auto">
          <Filter className="w-4 h-4 text-slate-500 mr-1 hidden sm:block" />
          {['ALL', 'PENDING', 'APPROVED', 'REJECTED'].map((status) => (
            <button
              key={status}
              onClick={() => setFilterStatus(status)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                filterStatus === status
                  ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
                  : 'bg-slate-950 border border-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              {status}
            </button>
          ))}
        </div>
      </div>

      {/* Main Leave Requests Table */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="text-xs uppercase bg-slate-950/80 text-slate-400 border-b border-slate-800">
              <tr>
                <th className="py-3.5 px-4 font-semibold">Request ID</th>
                <th className="py-3.5 px-4 font-semibold">Employee</th>
                <th className="py-3.5 px-4 font-semibold">Leave Type</th>
                <th className="py-3.5 px-4 font-semibold">Date Range</th>
                <th className="py-3.5 px-4 font-semibold">Reason</th>
                <th className="py-3.5 px-4 font-semibold">Status</th>
                <th className="py-3.5 px-4 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-500 text-sm">
                    Loading leave requests...
                  </td>
                </tr>
              ) : filteredRequests.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-500 text-sm">
                    No leave requests found matching the current criteria.
                  </td>
                </tr>
              ) : (
                filteredRequests.map((req) => (
                  <tr key={req.request_id} className="hover:bg-slate-900/40 transition-colors">
                    {/* Request ID */}
                    <td className="py-4 px-4 font-mono text-xs font-semibold text-indigo-300 whitespace-nowrap">
                      {req.request_id}
                    </td>

                    {/* Employee Name & Role */}
                    <td className="py-4 px-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 text-xs font-bold">
                          {req.employee_name.charAt(0)}
                        </div>
                        <div>
                          <div className="font-semibold text-white">{req.employee_name}</div>
                          <div className="text-[11px] text-slate-400">{req.employee_id} • {req.employee_role}</div>
                        </div>
                      </div>
                    </td>

                    {/* Leave Type Badge */}
                    <td className="py-4 px-4 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold capitalize border ${
                          req.leave_type === 'urgent'
                            ? 'bg-rose-950/60 border-rose-800 text-rose-300'
                            : 'bg-slate-950 border-slate-800 text-slate-300'
                        }`}
                      >
                        {req.leave_type === 'urgent' && <AlertTriangle className="w-3 h-3 text-rose-400" />}
                        {req.leave_type}
                      </span>
                    </td>

                    {/* Date Range */}
                    <td className="py-4 px-4 whitespace-nowrap">
                      <div className="flex items-center gap-2 text-xs text-slate-200">
                        <Calendar className="w-3.5 h-3.5 text-slate-400" />
                        <span>{req.start_date}</span>
                        <span className="text-slate-500">→</span>
                        <span>{req.end_date}</span>
                      </div>
                      {req.session && req.session !== 'full_day' && (
                        <div className="text-[10px] text-amber-400 capitalize mt-0.5">
                          Session: {req.session}
                        </div>
                      )}
                    </td>

                    {/* Reason */}
                    <td className="py-4 px-4 max-w-xs">
                      <p className="text-xs text-slate-400 truncate" title={req.reason || 'No reason provided'}>
                        {req.reason || <span className="italic text-slate-600">No reason stated</span>}
                      </p>
                    </td>

                    {/* Status Badge */}
                    <td className="py-4 px-4 whitespace-nowrap">
                      <span
                        className={`px-2.5 py-1 rounded-full text-[11px] font-bold tracking-wider inline-flex items-center gap-1 ${
                          req.status === 'APPROVED'
                            ? 'bg-emerald-950/80 border border-emerald-800 text-emerald-400'
                            : req.status === 'REJECTED'
                            ? 'bg-rose-950/80 border border-rose-800 text-rose-400'
                            : 'bg-amber-950/80 border border-amber-800 text-amber-400 animate-pulse'
                        }`}
                      >
                        {req.status}
                      </span>
                    </td>

                    {/* Action Buttons */}
                    <td className="py-4 px-4 text-right whitespace-nowrap">
                      {req.status === 'PENDING' ? (
                        <div className="flex items-center justify-end gap-2">
                          <button
                            disabled={processingId === req.request_id}
                            onClick={() => handleReview(req.request_id, 'APPROVED')}
                            className="flex items-center gap-1 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white px-3 py-1.5 rounded-xl text-xs font-semibold transition-colors"
                          >
                            <Check className="w-3.5 h-3.5" />
                            Approve
                          </button>
                          <button
                            disabled={processingId === req.request_id}
                            onClick={() => handleReview(req.request_id, 'REJECTED')}
                            className="flex items-center gap-1 bg-rose-600/20 hover:bg-rose-600/40 border border-rose-800/80 border-rose-700 disabled:opacity-50 text-rose-300 px-3 py-1.5 rounded-xl text-xs font-semibold transition-colors"
                          >
                            <X className="w-3.5 h-3.5" />
                            Reject
                          </button>
                        </div>
                      ) : (
                        <span className="text-xs text-slate-500 italic">
                          Reviewed by {req.reviewed_by || 'Admin'}
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default LeaveManagement;