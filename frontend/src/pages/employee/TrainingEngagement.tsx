import React, { useState, useEffect, useCallback } from 'react';
import { 
  Loader2, 
  AlertCircle, 
  Clock, 
  Hourglass, 
  BookOpen, 
  CheckCircle, 
  ChevronRight, 
  Check, 
  X, 
  Calendar, 
  Layers, 
  Users, 
  GraduationCap 
} from 'lucide-react';

// Reusable Dark Card Component matching Dashboard style
const Card: React.FC<{ title: string; subtitle?: string; children: React.ReactNode }> = ({ title, subtitle, children }) => (
  <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 shadow-xl space-y-4 backdrop-blur-sm">
    <div>
      <h3 className="text-base font-bold text-white tracking-tight">{title}</h3>
      {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
    </div>
    {children}
  </div>
);

// Reusable Dark Badge Component
const Badge: React.FC<{ label: string; variant?: 'indigo' | 'emerald' | 'amber' | 'rose' | 'slate'; size?: 'sm' | 'md' }> = ({
  label,
  variant = 'indigo',
  size = 'sm',
}) => {
  const styles = {
    indigo: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
    emerald: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    amber: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    rose: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
    slate: 'bg-slate-900 text-slate-300 border-slate-800',
  };
  const sizeStyles = size === 'md' ? 'px-2.5 py-1 text-xs' : 'px-2 py-0.5 text-[10px]';

  return (
    <span className={`inline-flex items-center font-medium rounded-md border ${styles[variant]} ${sizeStyles}`}>
      {label}
    </span>
  );
};

// Interfaces
interface Proposal {
  id: string;
  engagementId: string;
  projectTitle: string;
  role: string;
  score: number;
  status: string;
  description: string;
  requiredSkills: string[];
  dueDate: string;
  type: string;
}

interface ActiveEngagement {
  id: string;
  title: string;
  role: string;
  currentMilestone: string;
  progressPercentage: number;
  nextSyncDate: string;
  status: string;
  interns?: string[];
}

interface AssignedBatch {
  batch_id: number;
  batch_name: string;
  domain: string;
  start_date: string;
  end_date: string;
  delivery_mode: string;
  status: string;
  mentor_id: number;
}

interface TrainingBatch {
  id: string;
  batchName: string;
  courseTitle: string;
  assignedRole: string;
  startDate: string;
  endDate: string;
  status: string;
  totalEnrolled: number;
}

export const TrainingAllocationsDashboard: React.FC<{ propEmployeeId?: string }> = ({ propEmployeeId }) => {
  const [activeTab, setActiveTab] = useState<'engagements' | 'batches'>('engagements');
  const [loading, setLoading] = useState<boolean>(true);
  const [usingFallback, setUsingFallback] = useState<boolean>(false);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState<boolean>(false);

  // Training Engagements State
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [waitingConfirmations, setWaitingConfirmations] = useState<Proposal[]>([]);
  const [activeEngagements, setActiveEngagements] = useState<ActiveEngagement[]>([]);
  const [completedEngagements, setCompletedEngagements] = useState<ActiveEngagement[]>([]);

  // Training Batches State
  const [trainingBatches, setTrainingBatches] = useState<TrainingBatch[]>([]);

  // Helper to extract Active Employee ID
  const getActiveEmployeeId = useCallback((): string => {
    if (propEmployeeId) return propEmployeeId;
    const authUserRaw = localStorage.getItem('auth_user');
    if (authUserRaw) {
      try {
        const user = JSON.parse(authUserRaw);
        return user.employee_id || user.id || user.resource_id || '';
      } catch (e) {
        console.error('Error parsing auth_user', e);
      }
    }
    return '';
  }, [propEmployeeId]);

  // Fetch Allocated Student Batches for logged in mentor
  const fetchAllocatedBatches = useCallback(async (headers: HeadersInit) => {
    try {
      const authUserRaw = localStorage.getItem('auth_user');
      let userEmail = '';
      if (authUserRaw) {
        try {
          const user = JSON.parse(authUserRaw);
          userEmail = user.email || '';
        } catch (e) {
          console.error('Error parsing auth_user for email', e);
        }
      }

      if (!userEmail) return;

      const res = await fetch(
        `/api/allocations/student-batches/my-allocated-batches?email=${encodeURIComponent(userEmail)}`,
        { headers }
      );

      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data)) {
          setTrainingBatches(data);
        }
      }
    } catch (err) {
      console.error('Error fetching allocated student batches:', err);
    }
  }, []);

  // Fetch Training & Batch Data
  const fetchDashboardData = useCallback(async () => {
    setLoading(true);
    const targetEmployeeId = getActiveEmployeeId();

    const rawToken = localStorage.getItem('auth_token');
    let token = rawToken;
    if (rawToken) {
      try {
        const parsed = JSON.parse(rawToken);
        token = parsed.token || parsed.access_token || rawToken;
      } catch {
        token = rawToken;
      }
    }

    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };

    // Trigger allocated batches fetch alongside dashboard data
    await fetchAllocatedBatches(headers);

    try {
      const endpoint = `/api/allocations/my-allocations${targetEmployeeId ? `?resource_id=${targetEmployeeId}` : ''}`;
      const allocRes = await fetch(endpoint, { headers });

      if (allocRes.ok) {
        const data = await allocRes.json();
        const rawAllocations = Array.isArray(data) ? data : (data.allocations || data.data || []);

        if (Array.isArray(rawAllocations)) {
          // A. Separate Engagements vs Round Robin Batches
          const trainingAllocations = rawAllocations.filter((a: any) => 
            ['training', 'engagement', 'webinar', 'workshop'].includes(String(a.reference_type || '').toLowerCase())
          );
        

          // 1. Pending Proposals
          const fetchedProposals: Proposal[] = trainingAllocations
            .filter((a: any) => ['proposed', 'pending'].includes(String(a.status || '').toLowerCase()))
            .map((a: any) => ({
              id: String(a.allocation_id || a.id),
              engagementId: String(a.reference_id || ''),
              projectTitle: a.title || 'Training Workshop',
              role: a.role_on_project || a.role || 'Session Lead',
              score: typeof a.match_score === 'number' ? Math.round(a.match_score * 100) : 92.0,
              status: 'proposed',
              description: a.description || 'Assigned technical training workshop engagement.',
              requiredSkills: Array.isArray(a.tech_stack) ? a.tech_stack : (a.skills || ['Mentoring']),
              dueDate: a.start_date || a.due_date || 'N/A',
              type: a.reference_type || 'training',
            }));

          // 2. Waiting Admin Confirmation
          const fetchedWaiting: Proposal[] = trainingAllocations
            .filter((a: any) => ['accepted', 'accepted_by_employee'].includes(String(a.status || '').toLowerCase()))
            .map((a: any) => ({
              id: String(a.allocation_id || a.id),
              engagementId: String(a.reference_id || ''),
              projectTitle: a.title || 'Training Workshop',
              role: a.role_on_project || a.role || 'Session Lead',
              score: typeof a.match_score === 'number' ? Math.round(a.match_score * 100) : 92.0,
              status: 'accepted_by_employee',
              description: a.description || 'Accepted request awaiting final admin approval.',
              requiredSkills: Array.isArray(a.tech_stack) ? a.tech_stack : (a.skills || ['Mentoring']),
              dueDate: a.start_date || 'N/A',
              type: a.reference_type || 'training',
            }));

          // 3. Active Engagements
          const fetchedActive: ActiveEngagement[] = trainingAllocations
            .filter((a: any) => ['assigned', 'confirmed', 'active', 'approved', 'in_progress'].includes(String(a.status || '').toLowerCase()))
            .map((a: any) => ({
              id: String(a.project_id || a.allocation_id || a.id),
              title: a.title || 'Active Training Session',
              role: a.role_on_project || 'Lead Trainer',
              currentMilestone: a.current_milestone || 'Curriculum Delivery',
              progressPercentage: typeof a.progress_percentage === 'number' ? a.progress_percentage : 40,
              nextSyncDate: a.due_date || 'Next Live Session',
              status: 'in_progress',
              interns: a.interns || ['Batch Trainees'],
            }));

          // 4. Completed Engagements
          const fetchedCompleted: ActiveEngagement[] = trainingAllocations
            .filter((a: any) => ['completed', 'done', 'finished'].includes(String(a.status || '').toLowerCase()))
            .map((a: any) => ({
              id: String(a.project_id || a.allocation_id || a.id),
              title: a.title || 'Completed Training',
              role: a.role_on_project || 'Lead Trainer',
              currentMilestone: 'Completed',
              progressPercentage: 100,
              nextSyncDate: 'Finalized',
              status: 'completed',
              interns: a.interns || ['Batch Trainees'],
            }));

          

          setProposals(fetchedProposals);
          setWaitingConfirmations(fetchedWaiting);
          setActiveEngagements(fetchedActive);
          setCompletedEngagements(fetchedCompleted);
          setUsingFallback(false);
        }
      } else {
        setUsingFallback(true);
      }
    } catch (err) {
      console.error('Error fetching training data:', err);
      setUsingFallback(true);
    } finally {
      setLoading(false);
    }
  }, [getActiveEmployeeId, fetchAllocatedBatches]);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  // Action: Accept Training Proposal
  const handleProposalAction = async (id: string, action: 'accept') => {
    setActionLoadingId(id);
    const proposal = proposals.find((p) => p.id === id);
    if (!proposal) return;

    const targetEmployeeId = getActiveEmployeeId();
    try {
      await fetch(`/api/allocations/${id}/respond`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          status: 'accepted',
          employee_id: targetEmployeeId,
        }),
      });
    } catch (err) {
      console.warn('Network issue during accept:', err);
    } finally {
      setActionLoadingId(null);
    }

    setProposals((prev) => prev.filter((p) => p.id !== id));
    setWaitingConfirmations((prev) => [{ ...proposal, status: 'accepted_by_employee' }, ...prev]);
  };

  // Action: Reject Training Proposal
  const handleRejectionAction = async (id: string, action: 'reject') => {
    setActionLoadingId(id);
    const targetEmployeeId = getActiveEmployeeId();

    try {
      await fetch(`/api/allocations/${id}/respond`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          status: 'rejected_by_employee',
          employee_id: targetEmployeeId,
        }),
      });
    } catch (err) {
      console.warn('Network issue during reject:', err);
    } finally {
      setActionLoadingId(null);
    }

    setProposals((prev) => prev.filter((p) => p.id !== id));
  };

  // Action: Mark Active Training Engagement as Completed
  const handleUpdateEngagementStatus = async (engagementId: string, newStatus: string) => {
    setIsUpdatingStatus(true);
    try {
      const activeObj = activeEngagements.find((a) => a.id === engagementId);
      if (activeObj) {
        setActiveEngagements((prev) => prev.filter((a) => a.id !== engagementId));
        setCompletedEngagements((prev) => [
          { ...activeObj, status: 'completed', progressPercentage: 100, currentMilestone: 'Completed' },
          ...prev,
        ]);
      }
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-3">
        <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
        <p className="text-slate-400 text-sm font-medium">Loading Training Data...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="border-b border-slate-800/80 pb-5 flex justify-between items-end">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <GraduationCap className="w-7 h-7 text-indigo-400" />
            Training & Workshop Dashboard
          </h1>
          <p className="text-slate-400 text-xs sm:text-sm mt-1">
            Review training proposals, handle session engagements, and monitor round-robin assigned training batches.
          </p>
        </div>

        {usingFallback && (
          <span className="text-[11px] bg-amber-950/60 border border-amber-800/60 text-amber-300 px-2.5 py-1 rounded-lg flex items-center gap-1.5">
            <AlertCircle className="w-3.5 h-3.5 text-amber-400" /> Demo Mode (Mock Data)
          </span>
        )}
      </div>

      {/* TABS HEADER */}
      <div className="flex space-x-2 border-b border-slate-800/80 pb-3">
        <button
          onClick={() => setActiveTab('engagements')}
          className={`px-4 py-2 text-xs font-semibold rounded-lg flex items-center gap-2 transition-all ${
            activeTab === 'engagements'
              ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-950/50'
              : 'bg-slate-900 text-slate-400 hover:text-white hover:bg-slate-800 border border-slate-800'
          }`}
        >
          <BookOpen className="w-4 h-4" />
          Training Engagements
          {(proposals.length > 0 || waitingConfirmations.length > 0) && (
            <span className="bg-indigo-950 text-indigo-300 text-[10px] px-2 py-0.5 rounded-full border border-indigo-700/50 font-bold">
              {proposals.length + waitingConfirmations.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('batches')}
          className={`px-4 py-2 text-xs font-semibold rounded-lg flex items-center gap-2 transition-all ${
            activeTab === 'batches'
              ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-950/50'
              : 'bg-slate-900 text-slate-400 hover:text-white hover:bg-slate-800 border border-slate-800'
          }`}
        >
          <Layers className="w-4 h-4" />
          Training Batches (Round Robin)
          {trainingBatches.length > 0 && (
            <span className="bg-emerald-950 text-emerald-400 text-[10px] px-2 py-0.5 rounded-full border border-emerald-700/50 font-bold">
              {trainingBatches.length}
            </span>
          )}
        </button>
      </div>

      {/* ======================================================== */}
      {/* TAB 1: TRAINING ENGAGEMENTS */}
      {/* ======================================================== */}
      {activeTab === 'engagements' && (
        <div className="space-y-6">
          {/* SECTION 1: PROPOSALS */}
          <Card
            title={`Training Proposals (${proposals.length} Pending)`}
            subtitle="Accepting a proposal provisions the workshop schedule and assigns trainees."
          >
            <div className="space-y-4">
              {proposals.length === 0 ? (
                <div className="text-center py-8 text-slate-500 text-sm border border-dashed border-slate-800 rounded-xl">
                  No pending training proposals found.
                </div>
              ) : (
                proposals.map((item) => (
                  <div
                    key={item.id}
                    className={`p-5 bg-slate-950 border rounded-xl space-y-4 transition-all ${
                      item.status === 'proposed'
                        ? 'border-indigo-500/30 shadow-md shadow-indigo-950/10'
                        : 'border-slate-800 opacity-80'
                    }`}
                  >
                    <div className="flex justify-between items-start gap-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="font-bold text-white text-base">{item.projectTitle}</h4>
                          <span className="text-xs px-2 py-0.5 rounded-md bg-indigo-500/10 text-indigo-400 font-medium border border-indigo-500/20">
                            {item.role}
                          </span>
                        </div>
                        <p className="text-xs text-slate-300 mt-1">{item.description}</p>
                      </div>
                      <Badge label={`${item.score}% Match`} variant="emerald" size="md" />
                    </div>

                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {item.requiredSkills.map((skill, idx) => (
                        <span key={idx} className="bg-slate-900 text-slate-300 text-[11px] px-2 py-0.5 rounded border border-slate-800">
                          {skill}
                        </span>
                      ))}
                    </div>

                    <div className="flex items-center justify-between pt-3 border-t border-slate-800 text-xs">
                      <span className="text-amber-400 flex items-center gap-1.5 font-mono">
                        <Clock className="w-3.5 h-3.5" /> Start Date: {item.dueDate}
                      </span>

                      {item.status === 'proposed' ? (
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleRejectionAction(item.id, 'reject')}
                            disabled={actionLoadingId === item.id}
                            className="px-3 py-1.5 bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 border border-rose-500/20 rounded-lg font-medium flex items-center gap-1.5 transition-all disabled:opacity-50"
                          >
                            <X className="w-3.5 h-3.5" /> Decline
                          </button>
                          <button
                            onClick={() => handleProposalAction(item.id, 'accept')}
                            disabled={actionLoadingId === item.id}
                            className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-semibold flex items-center gap-1.5 transition-all shadow-md shadow-indigo-950/50 disabled:opacity-50"
                          >
                            {actionLoadingId === item.id ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            ) : (
                              <Check className="w-3.5 h-3.5" />
                            )}
                            Accept Engagement
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
                ))
              )}
            </div>
          </Card>

          {/* SECTION 2: WAITING FOR ADMIN CONFIRMATION */}
          <Card
            title={`Waiting for Confirmation (${waitingConfirmations.length})`}
            subtitle="Training proposals accepted by you awaiting final admin approval"
          >
            <div className="space-y-4">
              {waitingConfirmations.length === 0 ? (
                <div className="text-center py-8 border border-dashed border-slate-800 rounded-xl">
                  <Clock className="w-6 h-6 text-slate-600 mx-auto mb-2" />
                  <p className="text-xs text-slate-500">No training engagements currently awaiting confirmation.</p>
                </div>
              ) : (
                waitingConfirmations.map((item) => (
                  <div
                    key={item.id}
                    className="p-4 bg-slate-950 rounded-xl border border-amber-500/30 space-y-3 transition-all hover:border-amber-500/50"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <h5 className="text-sm font-bold text-white flex items-center gap-2">
                          <Hourglass className="w-4 h-4 text-amber-400 animate-pulse" /> {item.projectTitle}
                        </h5>
                        <p className="text-xs text-slate-400 mt-0.5">{item.role}</p>
                      </div>
                      <span className="text-[10px] bg-amber-500/10 text-amber-400 px-2 py-0.5 rounded border border-amber-500/20 font-medium">
                        Pending Admin Approval
                      </span>
                    </div>

                    <p className="text-xs text-slate-400 line-clamp-2">{item.description}</p>

                    <div className="flex items-center justify-between text-xs pt-1 border-t border-slate-900 text-slate-400">
                      <span className="flex items-center gap-1 text-[11px]">
                        <Calendar className="w-3.5 h-3.5 text-slate-500" /> Target Start: {item.dueDate}
                      </span>
                      <span className="text-[11px] text-amber-400 font-medium">Awaiting Admin Action</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </Card>

          {/* SECTION 3: ACTIVE TRAINING ENGAGEMENTS */}
          <Card
            title={`Active Training Engagements (${activeEngagements.length})`}
            subtitle="Training sessions and workshops currently underway"
          >
            <div className="space-y-4">
              {activeEngagements.length === 0 ? (
                <div className="text-center py-8 border border-dashed border-slate-800 rounded-xl">
                  <BookOpen className="w-6 h-6 text-slate-600 mx-auto mb-2" />
                  <p className="text-xs text-slate-500">No active training engagements right now.</p>
                </div>
              ) : (
                activeEngagements.map((item) => (
                  <div key={item.id} className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-3">
                    <div className="flex justify-between items-start">
                      <div>
                        <h5 className="text-sm font-bold text-white flex items-center gap-2">
                          <BookOpen className="w-4 h-4 text-indigo-400" /> {item.title}
                        </h5>
                        <p className="text-xs text-slate-400 mt-0.5">{item.role}</p>
                      </div>
                      <span className="text-[10px] bg-slate-900 text-slate-300 px-2 py-0.5 rounded border border-slate-800">
                        {item.interns ? item.interns.length : 0} Session Trainees
                      </span>
                    </div>

                    <div className="space-y-1">
                      <div className="flex justify-between text-[11px]">
                        <span className="text-slate-400">{item.currentMilestone}</span>
                        <span className="text-indigo-400 font-mono font-bold">{item.progressPercentage}%</span>
                      </div>
                      <div className="w-full h-1.5 bg-slate-900 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-indigo-500 rounded-full transition-all duration-300"
                          style={{ width: `${item.progressPercentage}%` }}
                        />
                      </div>
                    </div>

                    <div className="flex items-center justify-between text-xs pt-2 border-t border-slate-900 text-slate-400">
                      <span className="flex items-center gap-1 text-[11px]">
                        <Calendar className="w-3.5 h-3.5" /> Next Session: {item.nextSyncDate}
                      </span>

                      <div className="flex items-center gap-2">
                        <button
                          disabled={isUpdatingStatus}
                          onClick={() => handleUpdateEngagementStatus(item.id, 'completed')}
                          className="bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-[11px] font-semibold px-2.5 py-1 rounded-lg flex items-center gap-1 transition-all disabled:opacity-50"
                        >
                          <CheckCircle className="w-3 h-3 text-emerald-400" />
                          Mark Completed
                        </button>

                        <button className="text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-semibold text-[11px]">
                          View Details <ChevronRight className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </Card>

          {/* SECTION 4: COMPLETED TRAINING ENGAGEMENTS */}
          <Card
            title={`Completed Training Engagements (${completedEngagements.length})`}
            subtitle="Training programs successfully completed"
          >
            <div className="space-y-4">
              {completedEngagements.length === 0 ? (
                <div className="text-center py-8 border border-dashed border-slate-800 rounded-xl">
                  <CheckCircle className="w-6 h-6 text-slate-600 mx-auto mb-2" />
                  <p className="text-xs text-slate-500">No completed training engagements yet.</p>
                </div>
              ) : (
                completedEngagements.map((item) => (
                  <div key={item.id} className="p-4 bg-slate-950 rounded-xl border border-emerald-950/50 space-y-3">
                    <div className="flex justify-between items-start">
                      <div>
                        <h5 className="text-sm font-bold text-white flex items-center gap-2">
                          <CheckCircle className="w-4 h-4 text-emerald-400" /> {item.title}
                        </h5>
                        <p className="text-xs text-slate-400 mt-0.5">{item.role}</p>
                      </div>
                      <span className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full font-semibold">
                        Completed
                      </span>
                    </div>

                    <div className="space-y-1">
                      <div className="flex justify-between text-[11px]">
                        <span className="text-slate-400">Finished</span>
                        <span className="text-emerald-400 font-mono font-bold">100%</span>
                      </div>
                      <div className="w-full h-1.5 bg-slate-900 rounded-full overflow-hidden">
                        <div className="h-full bg-emerald-500 rounded-full w-full" />
                      </div>
                    </div>

                    <div className="flex items-center justify-between text-xs pt-2 border-t border-slate-900 text-slate-400">
                      <span className="text-[11px] text-slate-500">Successfully finalized curriculum</span>
                      <button className="text-slate-400 hover:text-white flex items-center gap-1 font-semibold text-[11px]">
                        View Details <ChevronRight className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </Card>
        </div>
      )}

      {/* ======================================================== */}
{/* TAB 2: TRAINING BATCHES (ROUND ROBIN ASSIGNED) */}
{/* ======================================================== */}
{activeTab === 'batches' && (
  <div className="space-y-6">
    {/* INFORMATIONAL BANNER */}
    <div className="bg-indigo-950/40 border border-indigo-500/30 p-4 rounded-xl flex items-center gap-3">
      <Users className="w-5 h-5 text-indigo-400 flex-shrink-0" />
      <p className="text-xs text-indigo-300">
        Training batches are allocated using automated <strong>Round Robin System</strong> distribution. Batches assigned here are display-only and require no manual accept/decline action.
      </p>
    </div>

    <Card
      title={`Assigned Training Batches (${trainingBatches.length})`}
      subtitle="Automated round-robin batch assignments"
    >
      <div className="space-y-4">
        {trainingBatches.length === 0 ? (
          <div className="text-center py-10 border border-dashed border-slate-800 rounded-xl">
            <Layers className="w-8 h-8 text-slate-600 mx-auto mb-2" />
            <p className="text-xs text-slate-500">No training batches currently assigned to you.</p>
          </div>
        ) : (
          trainingBatches.map((batch: any, index: number) => {
            // Safe property extraction (supports camelCase, snake_case, or alternative API structures)
            const batchId = batch.id || batch._id || batch.batch_id || index;
            const batchName = batch.batchName || batch.batch_name || batch.name || 'Allocated Training Batch';
            const courseTitle = batch.courseTitle || batch.course_title || batch.course || 'Training Program';
            const totalEnrolled = batch.totalEnrolled ?? batch.total_enrolled ?? (Array.isArray(batch.students) ? batch.students.length : 0);
            const status = batch.status || 'Active';
            const assignedRole = batch.assignedRole || batch.assigned_role || batch.role || 'Lead Mentor / Trainer';
            const startDate = batch.startDate || batch.start_date || 'N/A';
            const endDate = batch.endDate || batch.end_date || 'N/A';

            return (
              <div
                key={batchId}
                className="p-5 bg-slate-950 border border-slate-800 rounded-xl space-y-3 transition-all hover:border-indigo-500/40"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="font-bold text-white text-base flex items-center gap-2">
                        <Layers className="w-4 h-4 text-emerald-400" />
                        {batchName}
                      </h4>
                      <span className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-md font-mono">
                        {totalEnrolled} Trainees Enrolled
                      </span>
                    </div>
                    <p className="text-xs text-indigo-400 mt-1 font-medium">{courseTitle}</p>
                  </div>

                  <span className="text-[10px] bg-slate-900 text-slate-300 px-2.5 py-1 rounded-md border border-slate-800 font-semibold uppercase">
                    {status}
                  </span>
                </div>

                <div className="flex items-center gap-2 text-xs text-slate-400">
                  <span className="text-slate-500">Assigned Role:</span>
                  <span className="text-slate-200 font-medium">{assignedRole}</span>
                </div>

                <div className="flex items-center justify-between text-xs pt-3 border-t border-slate-900 text-slate-400">
                  <span className="flex items-center gap-1.5 text-[11px]">
                    <Calendar className="w-3.5 h-3.5 text-slate-500" />
                    Duration: <span className="text-slate-300 font-mono">{startDate}</span> to{' '}
                    <span className="text-slate-300 font-mono">{endDate}</span>
                  </span>

                  <button className="text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-semibold text-[11px]">
                    View Batch Roster <ChevronRight className="w-3 h-3" />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </Card>
  </div>
)}

    </div>);}

export default TrainingAllocationsDashboard;