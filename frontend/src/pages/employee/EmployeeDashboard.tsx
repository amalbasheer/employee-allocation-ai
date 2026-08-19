import React, { useState, useEffect, useCallback } from 'react';
import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';

import { 
  Check, X, Clock, Briefcase, Video, Calendar, 
  ExternalLink, ChevronRight, Loader2, AlertCircle
} from 'lucide-react';

export interface Proposal {
  id: string;
  projectId: string;
  projectTitle: string;
  role: string;
  score: number;
  status: 'proposed' | 'accepted_by_employee' | 'rejected_by_employee';
  description: string;
  assignedInterns: string[];
  requiredSkills: string[];
  dueDate: string;
}

export interface ActiveProject {
  id: string;
  title: string;
  role: string;
  interns: string[];
  currentMilestone: string;
  progressPercentage: number;
  nextSyncDate: string;
}

export interface Webinar {
  id: string;
  title: string;
  date: string;
  time: string;
  attendeesCount: number;
  meetingUrl: string;
}

// Fallback Mock Data
const initialProposals: Proposal[] = [
  {
    id: 'alloc-1',
    projectId: 'p-101',
    projectTitle: 'LLM Fine-Tuning Pipeline',
    role: 'Lead AI Mentor',
    score: 95.4,
    status: 'proposed',
    description: 'Supervise 2 interns building domain-specific LoRA adapters for document summarization.',
    assignedInterns: ['John Doe (Stanford)', 'Maya Patel (MIT)'],
    requiredSkills: ['PyTorch', 'LoRA', 'FastAPI'],
    dueDate: '24 hours remaining',
  },
];

const initialActiveProjects: ActiveProject[] = [
  {
    id: 'p-act-10',
    title: 'Computer Vision Edge API',
    role: 'Lead Mentor',
    interns: ['Elena R.', 'Marcus K.'],
    currentMilestone: 'Milestone 2: Model Quantization',
    progressPercentage: 65,
    nextSyncDate: 'Tomorrow, 2:00 PM',
  },
];

const initialWebinars: Webinar[] = [
  {
    id: 'web-101',
    title: 'Advanced PyTorch & CUDA Optimization',
    date: 'Aug 24, 2026',
    time: '10:00 AM - 11:30 AM EST',
    attendeesCount: 34,
    meetingUrl: 'https://meet.company.com/pytorch-tuning',
  },
];

interface EmployeeDashboardProps {
  employeeId?: string;
}

export const EmployeeDashboard: React.FC<EmployeeDashboardProps> = ({ 
  employeeId = 'rp2-emp-0001' 
}) => {
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [activeProjects, setActiveProjects] = useState<ActiveProject[]>([]);
  const [webinars, setWebinars] = useState<Webinar[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [usingFallback, setUsingFallback] = useState<boolean>(false);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);

  // Fetch Dashboard Data from API for Allocations, use Mock ONLY for Webinars
const fetchDashboardData = useCallback(async () => {
  setLoading(true);

  // 1. Get Auth Token stored in localStorage under 'auth_token'
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

  try {
    // 2. Fetch Allocations from DB
    const allocRes = await fetch(
      `/api/allocations/my-allocations${employeeId ? `?employee_id=${employeeId}` : ''}`,
      { headers }
    );

    if (allocRes.ok) {
      const data = await allocRes.json();
      console.log('Real DB Response for Allocations:', data); // Inspect exact output in DevTools Console

      // Normalize if backend wraps array inside { data: [...] } or { allocations: [...] }
      const rawAllocations = Array.isArray(data)
        ? data
        : (data.allocations || data.data || []);

      if (Array.isArray(rawAllocations)) {
        // Map DB allocations to Proposal interface
        const fetchedProposals: Proposal[] = rawAllocations
          .filter((a: any) => {
            const s = String(a.status || '').toLowerCase();
            return s === 'proposed' || s === 'pending';
          })
          .map((a: any) => ({
            id: a.allocation_id || a.id,
            projectId: a.project_id || a.projectId,
            projectTitle: a.project_title || a.projectTitle || 'Project ' + (a.project_id || a.id),
            role: a.role || 'Project Mentor',
            score: a.match_score ? Math.round(a.match_score * 100) / 100 : 92.0,
            status: 'proposed',
            description: a.project_description || a.description || 'Assigned allocation request.',
            assignedInterns: a.interns || ['Assigned Interns'],
            requiredSkills: a.required_skills || ['Python', 'SQL'],
            dueDate: a.due_date || '48 hours remaining',
          }));

        // Map DB active allocations to ActiveProject interface
        const fetchedActive: ActiveProject[] = rawAllocations
          .filter((a: any) => {
            const s = String(a.status || '').toLowerCase();
            return ['assigned', 'accepted', 'active', 'approved', 'in_progress'].includes(s);
          })
          .map((a: any) => ({
            id: a.project_id || a.allocation_id || a.id,
            title: a.project_title || a.title || 'Active Project',
            role: a.role || 'Lead Mentor',
            interns: a.interns || ['Elena R.', 'Marcus K.'],
            currentMilestone: a.current_milestone || 'Milestone 1: Project Kickoff',
            progressPercentage: a.progress_percentage ?? 25,
            nextSyncDate: a.next_sync_date || 'Next Week',
          }));

        // Set real DB state (even if 0 records exist)
        setProposals(fetchedProposals);
        setActiveProjects(fetchedActive);
        setUsingFallback(false);
      }
    } else {
      console.error(`API Error ${allocRes.status}: Using demo fallback for projects.`);
      setProposals(initialProposals);
      setActiveProjects(initialActiveProjects);
      setUsingFallback(true);
    }
  } catch (err) {
    console.error('Network Error: Using demo fallback for projects.', err);
    setProposals(initialProposals);
    setActiveProjects(initialActiveProjects);
    setUsingFallback(true);
  } finally {
    // 3. Webinars ALWAYS use mock data directly
    setWebinars(initialWebinars);
    setLoading(false);
  }
}, [employeeId]);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  // Action Handler: Accept or Reject Proposal
  const handleProposalAction = async (id: string, action: 'accept' | 'reject') => {
    setActionLoadingId(id);
    const proposal = proposals.find((p) => p.id === id);
    if (!proposal) return;

    const newStatus = action === 'accept' ? 'accepted_by_employee' : 'rejected_by_employee';

    try {
      // 1. Try Backend Update Endpoint
      const response = await fetch(`/api/allocations/${id}/respond`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          status: action === 'accept' ? 'accepted' : 'rejected',
          employee_id: employeeId,
        }),
      });

      if (!response.ok) {
        // Fallback endpoint if custom response endpoint isn't present
        await fetch(`/api/allocations/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: action === 'accept' ? 'accepted' : 'rejected' }),
        });
      }
    } catch (err) {
      console.warn('Failed to persist action to server, updating UI locally:', err);
    } finally {
      setActionLoadingId(null);
    }

    // 2. Local State UI Transition
    if (action === 'accept') {
      const newActiveProject: ActiveProject = {
        id: `act-${Date.now()}`,
        title: proposal.projectTitle,
        role: proposal.role,
        interns: proposal.assignedInterns,
        currentMilestone: 'Milestone 1: Project Onboarding',
        progressPercentage: 10,
        nextSyncDate: 'Sep 02, 2026',
      };

      const newWebinar: Webinar = {
        id: `web-${Date.now()}`,
        title: `${proposal.projectTitle}: Onboarding Workshop`,
        date: 'Sep 04, 2026',
        time: '11:00 AM EST',
        attendeesCount: proposal.assignedInterns.length + 1,
        meetingUrl: 'https://meet.company.com/onboarding',
      };

      setActiveProjects((prev) => [newActiveProject, ...prev]);
      setWebinars((prev) => [newWebinar, ...prev]);
    }

    setProposals((prev) =>
      prev.map((p) => (p.id === id ? { ...p, status: newStatus } : p))
    );
  };

  const pendingCount = proposals.filter((p) => p.status === 'proposed').length;

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-3">
        <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
        <p className="text-slate-400 text-sm font-medium">Loading Dashboard Data...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="border-b border-slate-800/80 pb-5 flex justify-between items-end">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Employee & Mentor Dashboard</h1>
          <p className="text-slate-400 text-xs sm:text-sm mt-1">
            Review incoming proposals, track active mentorships, and manage live technical sessions.
          </p>
        </div>

        {usingFallback && (
          <span className="text-[11px] bg-amber-950/60 border border-amber-800/60 text-amber-300 px-2.5 py-1 rounded-lg flex items-center gap-1.5">
            <AlertCircle className="w-3.5 h-3.5 text-amber-400" /> Demo Mode (Mock Data)
          </span>
        )}
      </div>

      {/* PROPOSALS SECTION */}
      <Card
        title={`My Proposals (${pendingCount} Pending)`}
        subtitle="Accepting a proposal provisions project workspace and schedules kickoff sessions."
      >
        <div className="space-y-4">
          {proposals.length === 0 ? (
            <div className="text-center py-8 text-slate-500 text-sm">
              No pending project proposals found.
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
                    <Clock className="w-3.5 h-3.5" /> {item.dueDate}
                  </span>

                  {item.status === 'proposed' ? (
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleProposalAction(item.id, 'reject')}
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
                        Accept Proposal
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

      {/* ACTIVE PROJECTS & WEBINARS GRID */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card title="Active Projects" subtitle="Projects currently active and underway">
          <div className="space-y-4">
            {activeProjects.map((project) => (
              <div key={project.id} className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-3">
                <div className="flex justify-between items-start">
                  <div>
                    <h5 className="text-sm font-bold text-white flex items-center gap-2">
                      <Briefcase className="w-4 h-4 text-indigo-400" /> {project.title}
                    </h5>
                    <p className="text-xs text-slate-400 mt-0.5">{project.role}</p>
                  </div>
                  <span className="text-[10px] bg-slate-900 text-slate-300 px-2 py-0.5 rounded border border-slate-800">
                    {project.interns.length} Mentees
                  </span>
                </div>

                <div className="space-y-1">
                  <div className="flex justify-between text-[11px]">
                    <span className="text-slate-400">{project.currentMilestone}</span>
                    <span className="text-indigo-400 font-mono font-bold">{project.progressPercentage}%</span>
                  </div>
                  <div className="w-full h-1.5 bg-slate-900 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-indigo-500 rounded-full transition-all duration-300"
                      style={{ width: `${project.progressPercentage}%` }}
                    />
                  </div>
                </div>

                <div className="flex items-center justify-between text-xs pt-1 text-slate-400">
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5" /> Sync: {project.nextSyncDate}
                  </span>
                  <button className="text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-semibold text-[11px]">
                    View Details <ChevronRight className="w-3 h-3" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card title="Webinars & Sessions" subtitle="Workshops and technical sessions">
          <div className="space-y-4">
            {webinars.map((webinar) => (
              <div key={webinar.id} className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-3">
                <div className="flex justify-between items-start">
                  <div>
                    <h5 className="text-sm font-bold text-white flex items-center gap-2">
                      <Video className="w-4 h-4 text-amber-400" /> {webinar.title}
                    </h5>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {webinar.date} • {webinar.time}
                    </p>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-slate-900 text-xs">
                  <a
                    href={webinar.meetingUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="bg-indigo-600/10 text-indigo-400 hover:bg-indigo-600/20 text-xs font-semibold px-3 py-1.5 rounded-lg border border-indigo-500/20 flex items-center gap-1.5 transition-all"
                  >
                    Launch Session <ExternalLink className="w-3 h-3 text-indigo-400" />
                  </a>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
};