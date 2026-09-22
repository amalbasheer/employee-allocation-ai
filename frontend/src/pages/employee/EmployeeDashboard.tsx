import React, { useState, useEffect, useCallback } from 'react';
import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import api from '../../services/api';

import { 
  Check, X, Clock, Briefcase, Video, Calendar, Hourglass, Flag,
  ExternalLink, ChevronRight, Loader2, AlertCircle, CheckCircle, Edit2,
} from 'lucide-react';

export type ProjectStatus = 'open' | 'completed' |'in_progress';
export type AllocatedStatus = 'proposed' | 'accepted' |'rejected' | 'assigned' | 'substituted' | 'unassigned';

export interface MilestoneObject {
  id?: string;
  key?: string;
  name?: string;
  title?: string;
}

export interface Project {
  id: string;
  name: string;
  category: string;
  project_type: string;
  status: ProjectStatus;
  description: string;
  requiredSkills?: string[];
  startDate: string;
  endDate?: string;
  requiredHoursPerWeek?: number;
  priorityLevel?: string;
  proposedMentorId?: string;
  proposedMentorName?: string;
  allocationId?: string;
  reference_id?: string; // ID of the mentor allocation record
  allocatedStudentIds?: string[];
  allocatedStudentsname?: string[];
  proposedMentorStatus?: AllocatedStatus;
  completedMilestones?: string[];
  milestones?: (string | MilestoneObject)[];
  progressPercentage?: number;
  github_url?: string;
  deployed_url?: string;
}

export interface Proposal {
  id: string;
  projectId: string;
  projectTitle: string;
  role: string;
  score: number;
  status: string;
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
  completedMilestones: string[];
  progressPercentage: number;
  nextSyncDate: string;
  milestones?: (string | MilestoneObject)[];
  github_url?: string;
  deployed_url?: string;
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
    completedMilestones: ['Deployment'],
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
  employeeId: propEmployeeId 
}) => {
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [waitingConfirmations, setWaitingConfirmations] = useState<Proposal[]>([]);

  const [webinars, setWebinars] = useState<Webinar[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [usingFallback, setUsingFallback] = useState<boolean>(false);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);
  // 1. Declare state variables at the top
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  // 1. Resolve Active Employee ID Dynamically (Props -> localStorage -> Fallback)
  // Dynamically filtered from the main user-assigned projects array
  const [activeProjects, setActiveProjects] = useState<ActiveProject[]>([]);
  const pendingCount = proposals.filter((p) => p.status === 'proposed').length;
  const [completedProjects, setCompletedProjects] = useState<ActiveProject[]>([]);

  // States for Inline Project Links Editor
  const [editingProjectId, setEditingProjectId] = useState<string | null>(null);
  const [githubInput, setGithubInput] = useState<string>('');
  const [deployedInput, setDeployedInput] = useState<string>('');
  const [isSavingLinks, setIsSavingLinks] = useState<boolean>(false);

  const formatMilestoneLabel = (key: string): string => {
  return key
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

  // Milestone keys and their corresponding weight percentages (total = 100%)
  const MILESTONE_WEIGHTS: Record<string, number> = {
  project_kickoff: 5,
  architecture_design: 10,
  repo_cicd_setup: 10,
  core_development: 35,
  testing_code_review: 10,
  deployment: 15,
  documentation: 10,
  final_signoff: 5,
 };

  const calculateProgress = (completedKeys: string[]): number => {
    const total = completedKeys.reduce((sum, key) => sum + (MILESTONE_WEIGHTS[key] || 0), 0);
      return Math.min(100, total);
  };

  const API_BASE = import.meta.env.VITE_BACKEND_URL || 'https://employee-allocation-ai.onrender.com';
  
  const getActiveEmployeeId = useCallback((): string => {
    if (propEmployeeId) return propEmployeeId;

    const authUserRaw = localStorage.getItem('auth_user');
    if (authUserRaw) {
      try {
        const user = JSON.parse(authUserRaw);
        return user.employee_id || user.id || user.resource_id || '';
      } catch (e) {
        console.error('Error parsing auth_user from localStorage', e);
      }
    }
    return '';
  }, [propEmployeeId]);

  /**
 * Helper to get the current logged-in employee's name.
 * Checks localStorage cached profile, Supabase session metadata, or falls back to email username.
 */
 const getActiveEmployeeName = (): string => {
  try {
    // 1. Check direct user profile stored in localStorage
    const storedUser = 
      localStorage.getItem('user') || 
      localStorage.getItem('userProfile') || 
      localStorage.getItem('user_profile');

    if (storedUser) {
      const user = JSON.parse(storedUser);
      const name = user.name || user.full_name || user.user_metadata?.name || user.user_metadata?.full_name;
      if (name) return name;
      if (user.email) return user.email.split('@')[0];
    }

    // 2. Check Supabase auth session in localStorage if applicable
    const supabaseSessionKey = Object.keys(localStorage).find((key) =>
      key.startsWith('sb-') && key.endsWith('-auth-token')
    );

    if (supabaseSessionKey) {
      const sessionData = localStorage.getItem(supabaseSessionKey);
      if (sessionData) {
        const parsed = JSON.parse(sessionData);
        const metadata = parsed?.user?.user_metadata;
        const name = metadata?.name || metadata?.full_name;
        if (name) return name;
        if (parsed?.user?.email) return parsed.user.email.split('@')[0];
      }
    }
  } catch (error) {
    console.error('Error reading active employee name:', error);
  }

  // 3. Default fallback if no name or user found
  return 'Employee';
};

  // Fetch Dashboard Data from API for Project Allocations ONLY
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

  try {
    const endpoint = `${API_BASE}/api/allocations/my-allocations${targetEmployeeId ? `?resource_id=${targetEmployeeId}` : ''}`;
    const allocRes = await fetch(endpoint, { headers });

    if (allocRes.ok) {
      const data = await allocRes.json();
      console.log('Real DB Response for Allocations:', data);

      const rawAllocations = Array.isArray(data)
        ? data
        : (data.allocations || data.data || []);

      if (Array.isArray(rawAllocations)) {
        // FILTER: Keep ONLY allocations where reference_type === 'project'
        const projectAllocations = rawAllocations.filter((a: any) => {
          const refType = String(a.reference_type || 'project').toLowerCase();
          return refType === 'project';
        });

        // A. Map Proposed Project Allocations
        const fetchedProposals: Proposal[] = projectAllocations
          .filter((a: any) => {
            const s = String(a.status || '').toLowerCase();
            return s === 'proposed' || s === 'pending';
          })
          .map((a: any) => ({
            id: String(a.allocation_id || a.id),
            projectId: String(a.project_id || ''),
            projectTitle: a.title || 'Assigned Project',
            role: a.role || 'Project Mentor',
            score: typeof a.match_score === 'number' ? Math.round(a.match_score * 100) / 100 : 90.0,
            status: 'proposed',
            description: a.description || 'Assigned allocation request.',
            assignedInterns: a.interns || (a.mentor ? [a.mentor] : ['Assigned Interns']),
            requiredSkills: Array.isArray(a.tech_stack) ? a.tech_stack : ['Python', 'SQL'],
            dueDate: a.due_date || 'N/A',
          }));

        // B. Map Waiting Confirmations (Project Only)
        const fetchedWaiting: Proposal[] = projectAllocations
          .filter((a: any) => {
            const s = String(a.status || '').toLowerCase();
            return ['accepted', 'accepted_by_employee'].includes(s);
          })
          .map((a: any) => ({
            id: String(a.allocation_id || a.id),
            projectId: String(a.project_id || ''),
            projectTitle: a.title || 'Assigned Project',
            role: a.role || 'Project Mentor',
            score: typeof a.match_score === 'number' ? Math.round(a.match_score * 100) / 100 : 90.0,
            status: 'accepted',
            description: a.description || 'Assigned allocation request.',
            assignedInterns: a.interns || (a.mentor ? [a.mentor] : ['Assigned Interns']),
            requiredSkills: Array.isArray(a.tech_stack) ? a.tech_stack : ['Python', 'SQL'],
            dueDate: a.due_date || 'N/A',
          }));

        // C. Map Active Projects (Project Only)
        const fetchedActive: ActiveProject[] = projectAllocations
          .filter((a: any) => {
            const s = String(a.status || '').toLowerCase();
            return ['assigned', 'confirmed', 'active', 'approved', 'in_progress'].includes(s);
          })
          .map((a: any) => {
            // Parse completed milestone keys from backend
              const milestones = Array.isArray(a.completed_milestones)
                ? a.completed_milestones
                : (typeof a.completed_milestones === 'string'
                    ? JSON.parse(a.completed_milestones || '[]')
                    : []);

            return {id: String(a.project_id || a.allocation_id || a.id),
            title: a.title || 'Active Project',
            role: a.role || 'Lead Mentor',
            interns: a.interns || (a.mentor ? [a.mentor] : ['Assigned Team']),
            currentMilestone: a.current_milestone || 'Project Execution',
            completedMilestones: milestones,
            progressPercentage: typeof a.progress_percentage === 'number' ? a.progress_percentage : calculateProgress(milestones),
            nextSyncDate: a.due_date || 'Next Week',
            status: 'in_progress',
            milestones: a.milestones && a.milestones.length > 0 ? a.milestones : Object.keys(MILESTONE_WEIGHTS),
            github_url: a.github_url || '',
            deployed_url: a.deployed_url || '',  
          };
          });

        // D. Map Completed Projects (Project Only)
        const fetchedCompleted: ActiveProject[] = projectAllocations
          .filter((a: any) => {
            const s = String(a.status || '').toLowerCase();
            return ['completed', 'done', 'finished'].includes(s);
          })
          .map((a: any) => ({
            id: String(a.project_id || a.allocation_id || a.id),
            title: a.title || 'Completed Project',
            role: a.role || 'Lead Mentor',
            interns: a.interns || (a.mentor ? [a.mentor] : ['Assigned Team']),
            currentMilestone: 'Completed',
            completedMilestones: Object.keys(MILESTONE_WEIGHTS),
            progressPercentage: 100,
            nextSyncDate: 'Finished',
            status: 'completed',
            github_url: a.github_url || '',
            deployed_url: a.deployed_url || '',
          }));

        setProposals(fetchedProposals);
        setWaitingConfirmations(fetchedWaiting);
        setActiveProjects(fetchedActive);
        setCompletedProjects(fetchedCompleted);
        setUsingFallback(false);
      }
    } else {
      console.error(`API Error ${allocRes.status}: Using demo fallback for projects.`);
      setProposals(initialProposals);
      setActiveProjects(initialActiveProjects);
      setCompletedProjects([]);
      setUsingFallback(true);
    }
  } catch (err) {
    console.error('Network Error: Using demo fallback for projects.', err);
    setProposals(initialProposals);
    setActiveProjects(initialActiveProjects);
    setCompletedProjects([]);
    setUsingFallback(true);
  } finally {
    setLoading(false);
  }
}, [getActiveEmployeeId]);

useEffect(() => {
  fetchDashboardData();
}, [fetchDashboardData]);

// Link Handlers
  const handleStartEditLinks = (project: ActiveProject) => {
    setEditingProjectId(project.id);
    setGithubInput(project.github_url || '');
    setDeployedInput(project.deployed_url || '');
  };

  const handleSaveLinks = async (projectId: string) => {
    setIsSavingLinks(true);

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

    try {
      const response = await fetch(`${API_BASE}/api/projects/${projectId}/links`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          github_url: githubInput.trim(),
          deployed_url: deployedInput.trim(),
        }),
      });

      if (!response.ok) throw new Error('Failed to update project links');

      const updatedData = await response.json();
      const newGithub = updatedData.github_url || githubInput.trim();
      const newDeployed = updatedData.deployed_url || deployedInput.trim();

      // Update Active Projects locally
      setActiveProjects((prev) =>
        prev.map((proj) =>
          proj.id === projectId
            ? { ...proj, github_url: newGithub, deployed_url: newDeployed }
            : proj
        )
      );

      // Update Completed Projects locally
      setCompletedProjects((prev) =>
        prev.map((proj) =>
          proj.id === projectId
            ? { ...proj, github_url: newGithub, deployed_url: newDeployed }
            : proj
        )
      );

      setEditingProjectId(null);
    } catch (err: any) {
      alert(err.message || 'Error updating links');
    } finally {
      setIsSavingLinks(false);
    }
  };

// Handler: Toggle Milestone Status
  const handleToggleMilestone = async (projectId: string, milestoneKey: string) => {
    const targetProject = activeProjects.find(
      (p) => p.id === projectId || (p as any).projectId === projectId
    );
    if (!targetProject) return;

    const currentMilestones: string[] = (targetProject as any).completedMilestones || [];
    const isCompleted = currentMilestones.includes(milestoneKey);

    const updatedMilestones = isCompleted
      ? currentMilestones.filter((key) => key !== milestoneKey)
      : [...currentMilestones, milestoneKey];

    const newProgressPercentage = calculateProgress(updatedMilestones);

    // Optimistically update React State
    setActiveProjects((prev) =>
      prev.map((p) =>
        p.id === projectId || (p as any).projectId === projectId
          ? {
              ...p,
              completedMilestones: updatedMilestones,
              progressPercentage: newProgressPercentage,
            }
          : p
      )
    );

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
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/milestones`, {
        method: 'PATCH',
        headers,
        body: JSON.stringify({
          completed_milestones: updatedMilestones,
        }),
      });

      if (res.ok) {
        const updatedData = await res.json();
        setActiveProjects((prev) =>
          prev.map((p) =>
            p.id === projectId || (p as any).projectId === projectId
              ? {
                  ...p,
                  completedMilestones: updatedData.completed_milestones || updatedMilestones,
                  progressPercentage: updatedData.progress_percentage ?? newProgressPercentage,
                }
              : p
          )
        );
      } else {
        console.error(`API Error ${res.status}: Failed to update milestone on server.`);
      }
    } catch (err) {
      console.error('Network Error: Failed to persist milestone update.', err);
    }
  };

const [isUpdatingStatus, setIsUpdatingStatus] = useState<boolean>(false);

const handleUpdateProjectStatus = async (projectId: string, newStatus: string) => {
  try {
    const res = await api.patch(`${API_BASE}/api/projects/${projectId}/status`, {
      status: newStatus.toLowerCase(),
    });

    const updatedProject = res.data;

    // Update state directly from backend payload
    setActiveProjects((prevProjects) =>
      prevProjects.map((p) =>
        p.id === projectId
          ? {
              ...p,
              status: updatedProject.status,
              progressPercentage: updatedProject.progress_percentage ?? updatedProject.progress,
            }
          : p
      )
    );
  } catch (err: any) {
    console.error('Failed to update project status:', err);
  }
};

// Action Handler: Accept Proposal
const handleProposalAction = async (id: string, action: 'accept') => {
  setActionLoadingId(id);
  const proposal = proposals.find((p) => p.id === id);
  if (!proposal) return;

  const targetEmployeeId = getActiveEmployeeId();
  const targetEmployeeName = getActiveEmployeeName();
  const allocationStatus = action === 'accept' ? 'accepted' : 'accepted_by_employee';

  try {
    const response = await fetch(`${API_BASE}/api/allocations/${id}/respond`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        status: allocationStatus,
        employee_id: targetEmployeeId,
        employee_name: targetEmployeeName,
      }),
    });

    if (!response.ok) {
      await fetch(`${API_BASE}/api/allocations/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: allocationStatus }),
      });
    }
  } catch (err) {
    console.warn('Failed to persist action to server, updating UI locally:', err);
  } finally {
    setActionLoadingId(null);
  }

  // Update Local UI States
  setProposals((prev) => prev.filter((p) => p.id !== id));

  if (action === 'accept') {
    const acceptedProposal: Proposal = {
      ...proposal,
      status: 'accepted',
    };
    setWaitingConfirmations((prev) => [acceptedProposal, ...prev]);
  }
};

// Action Handler: Reject Proposal
const handleRejectionAction = async (id: string, action: 'reject') => {
  setActionLoadingId(id);
  const proposal = proposals.find((p) => p.id === id);
  if (!proposal) return;

  const targetEmployeeId = getActiveEmployeeId();
  const targetEmployeeName = getActiveEmployeeName();
  const allocationStatus = action === 'reject' ? 'rejected' : 'rejected_by_employee';

  try {
    const response = await fetch(`${API_BASE}/api/allocations/${id}/reject`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        status: allocationStatus,
        employee_id: targetEmployeeId,
        employee_name: targetEmployeeName,
      }),
    });

    if (!response.ok) {
      await fetch(`${API_BASE}/api/allocations/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: allocationStatus }),
      });
    }
  } catch (err) {
    console.warn('Failed to persist action to server, updating UI locally:', err);
  } finally {
    setActionLoadingId(null);
  }

  // Update Local UI States
  setProposals((prev) => prev.filter((p) => p.id !== id));
};

// Helper JSX Component to render hyperlinks or the input form inside project cards
const renderProjectLinksSection = (project: ActiveProject) => {
  const isEditingThisCard = editingProjectId === project.id;
  const hasLinks = Boolean(project.github_url || project.deployed_url);}

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
      {/* SECTION 2: WAITING FOR ADMIN CONFIRMATION */}
      <Card 
        title={`Waiting for Confirmation (${waitingConfirmations.length})`} 
        subtitle="Proposals accepted by you awaiting final admin approval"
      >
        <div className="space-y-4">
          {waitingConfirmations.length === 0 ? (
            <div className="text-center py-8 border border-dashed border-slate-800 rounded-xl">
              <Clock className="w-6 h-6 text-slate-600 mx-auto mb-2" />
              <p className="text-xs text-slate-500">No allocations currently awaiting confirmation.</p>
            </div>
          ) : (
            waitingConfirmations.map((project) => (
              <div 
                key={project.id} 
                className="p-4 bg-slate-950 rounded-xl border border-amber-500/30 space-y-3 transition-all hover:border-amber-500/50"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <h5 className="text-sm font-bold text-white flex items-center gap-2">
                      <Hourglass className="w-4 h-4 text-amber-400 animate-pulse" /> {project.projectTitle}
                    </h5>
                    <p className="text-xs text-slate-400 mt-0.5">{project.role}</p>
                  </div>
                  <span className="text-[10px] bg-amber-500/10 text-amber-400 px-2 py-0.5 rounded border border-amber-500/20 font-medium">
                    Pending Approval
                  </span>
                </div>

                <p className="text-xs text-slate-400 line-clamp-2">{project.description}</p>

                <div className="flex items-center justify-between text-xs pt-1 border-t border-slate-900 text-slate-400">
                  <span className="flex items-center gap-1 text-[11px]">
                    <Calendar className="w-3.5 h-3.5 text-slate-500" /> Target Start: {project.dueDate}
                  </span>
                  <span className="text-[11px] text-amber-400 font-medium">
                    Awaiting Admin Action
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </Card>

      {/* CARD 2: ACTIVE PROJECTS */}
<Card 
  title={`Active Projects (${activeProjects.length})`} 
  subtitle="Projects currently active and underway"
>
  <div className="space-y-4">
    {activeProjects.length === 0 ? (
      <div className="text-center py-8 border border-dashed border-slate-800 rounded-xl">
        <Briefcase className="w-6 h-6 text-slate-600 mx-auto mb-2" />
        <p className="text-xs text-slate-500">No confirmed active projects yet.</p>
      </div>
    ) : (
      activeProjects.map((project) => {
        // Format snake_case string labels to readable title case
        const formatLabel = (str: string) =>
          typeof str === 'string' && str.includes('_')
            ? str.split('_').map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
            : str;

        const activeStage = project.currentMilestone 
          ? formatLabel(project.currentMilestone) 
          : 'Not Set';

        const isEditingThisProject = editingProjectId === project.id;
        const hasLinks = Boolean(project.github_url || project.deployed_url);

        return (
          <div key={project.id} className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-3">
            {/* Header Info */}
            <div className="flex justify-between items-start">
              <div>
                <h5 className="text-sm font-bold text-white flex items-center gap-2">
                  <Briefcase className="w-4 h-4 text-indigo-400" /> {project.title}
                </h5>
                <p className="text-xs text-slate-400 mt-0.5">{project.role}</p>
              </div>
              <span className="text-[10px] bg-slate-900 text-slate-300 px-2 py-0.5 rounded border border-slate-800">
                {project.interns ? project.interns.length : 0} Mentees
              </span>
            </div>

            {/* PROGRESS & MILESTONES SECTION */}
            <div className="space-y-3">
              {/* Header & Percentage */}
              <div className="flex justify-between items-center text-[11px]">
                <div className="flex items-center gap-1.5 text-slate-400">
                  <Flag className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Active Stage:</span>
                  <span className="text-white font-semibold">
                    {activeStage}
                  </span>
                </div>
                <span className="text-indigo-400 font-mono font-bold">
                  {project.progressPercentage ?? 0}%
                </span>
              </div>

              {/* Progress Bar */}
              <div className="w-full h-1.5 bg-slate-900 rounded-full overflow-hidden">
                <div
                  className="h-full bg-indigo-500 rounded-full transition-all duration-300"
                  style={{ width: `${project.progressPercentage ?? 0}%` }}
                />
              </div>

              {/* Interactive Milestone Chips */}
              {(() => {
                const availableMilestones = project.milestones && project.milestones.length > 0
                  ? project.milestones
                  : Object.keys(MILESTONE_WEIGHTS);

                return (
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {availableMilestones.map((milestone: any) => {
                      const milestoneKey: string = 
                        typeof milestone === 'string' 
                          ? milestone 
                          : milestone?.key || milestone?.id || milestone?.name || '';

                      const rawLabel: string = 
                        typeof milestone === 'string' 
                          ? milestone 
                          : milestone?.name || milestone?.title || milestoneKey;

                      const milestoneLabel = formatLabel(rawLabel);
                      
                      const isCompleted = (project.completedMilestones || []).includes(milestoneKey);
                      const isCurrent = project.currentMilestone === milestoneKey || project.currentMilestone === rawLabel;

                      return (
                        <button
                          key={milestoneKey}
                          type="button"
                          onClick={() => handleToggleMilestone(project.id, milestoneKey)}
                          className={`text-[10px] px-2.5 py-1 rounded-md border flex items-center gap-1.5 transition-all cursor-pointer ${
                            isCompleted
                              ? 'bg-emerald-950/50 text-emerald-300 border-emerald-700/60 hover:bg-emerald-900/60'
                              : isCurrent
                              ? 'bg-indigo-950/80 text-indigo-300 border-indigo-500/60 ring-1 ring-indigo-500/30'
                              : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200 hover:border-slate-700'
                          }`}
                        >
                          {isCompleted ? (
                            <Check className="w-3 h-3 text-emerald-400 stroke-[3]" />
                          ) : (
                            <Clock className="w-3 h-3 opacity-60" />
                          )}
                          <span>{milestoneLabel}</span>
                        </button>
                      );
                    })}
                  </div>
                );
              })()}
            </div>

            {/* RESOURCE LINKS & INLINE EDITING SECTION */}
            {isEditingThisProject ? (
              <div className="p-3 bg-slate-900/90 rounded-lg border border-slate-800 space-y-2 text-xs">
                <p className="font-semibold text-slate-300 text-[11px]">Update Resource Links</p>
                <div>
                  <label className="text-[10px] text-slate-400 block mb-0.5">GitHub Repository URL</label>
                  <input
                    type="url"
                    placeholder="https://github.com/org/repo"
                    value={githubInput}
                    onChange={(e) => setGithubInput(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-xs text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-slate-400 block mb-0.5">Live Deployed App URL</label>
                  <input
                    type="url"
                    placeholder="https://myapp.vercel.app"
                    value={deployedInput}
                    onChange={(e) => setDeployedInput(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-xs text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div className="flex justify-end gap-2 pt-1">
                  <button
                    type="button"
                    onClick={() => setEditingProjectId(null)}
                    className="px-2.5 py-1 rounded text-[11px] bg-slate-800 text-slate-300 hover:bg-slate-700"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={() => handleSaveLinks(project.id)}
                    disabled={isSavingLinks}
                    className="px-2.5 py-1 rounded text-[11px] bg-indigo-600 text-white hover:bg-indigo-500 font-medium disabled:opacity-50"
                  >
                    {isSavingLinks ? 'Saving...' : 'Save Links'}
                  </button>
                </div>
              </div>
            ) : (
              <div className="pt-2 border-t border-slate-900 flex items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2">
                  {project.github_url ? (
                    <a
                      href={project.github_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-900 hover:bg-slate-800 border border-slate-800 text-[11px] font-medium text-purple-300 hover:text-purple-200 transition-colors"
                    >
                      <ExternalLink className="w-3 h-3 text-purple-400" />
                      GitHub
                    </a>
                  ) : null}

                  {project.deployed_url ? (
                    <a
                      href={project.deployed_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-emerald-950/40 hover:bg-emerald-900/50 border border-emerald-800/50 text-[11px] font-medium text-emerald-300 hover:text-emerald-200 transition-colors"
                    >
                      <ExternalLink className="w-3 h-3 text-emerald-400" />
                      Live App
                    </a>
                  ) : null}

                  {!hasLinks && (
                    <span className="text-[11px] text-slate-500 italic">No links added</span>
                  )}
                </div>

                <button
                  type="button"
                  onClick={() => handleStartEditLinks(project)}
                  className="text-[11px] text-indigo-400 hover:text-indigo-300 font-medium px-2 py-1 rounded hover:bg-slate-900 transition-colors flex items-center gap-1 cursor-pointer"
                >
                  <Edit2 className="w-3 h-3" />
                  {hasLinks ? 'Edit Links' : 'Add Links'}
                </button>
              </div>
            )}

            {/* Footer */}
            <div className="flex items-center justify-between text-xs pt-2 border-t border-slate-900 text-slate-400">
              <span className="flex items-center gap-1 text-[11px]">
                <Calendar className="w-3.5 h-3.5 text-slate-500" /> Sync: {project.nextSyncDate}
              </span>

              <div className="flex items-center gap-2">
                {/* STATUS UPDATE BUTTON */}
                <button
                  type="button"
                  disabled={isUpdatingStatus}
                  onClick={() => handleUpdateProjectStatus(project.id, 'completed')}
                  className="bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-[11px] font-semibold px-2.5 py-1 rounded-lg flex items-center gap-1 transition-all disabled:opacity-50 cursor-pointer"
                >
                  <CheckCircle className="w-3 h-3 text-emerald-400" />
                  Mark Completed
                </button>

              </div>
            </div>
          </div>
        );
      })
    )}
  </div>
</Card>

      {/* CARD 2: COMPLETED PROJECTS */}
  <Card 
    title={`Completed Projects (${completedProjects.length})`} 
    subtitle="Projects successfully finalized and delivered"
  >
    <div className="space-y-4">
      {completedProjects.length === 0 ? (
        <div className="text-center py-8 border border-dashed border-slate-800 rounded-xl">
          <CheckCircle className="w-6 h-6 text-slate-600 mx-auto mb-2" />
          <p className="text-xs text-slate-500">No completed projects yet.</p>
        </div>
      ) : (
        completedProjects.map((project) => (
          <div key={project.id || project.id} className="p-4 bg-slate-950 rounded-xl border border-emerald-950/50 space-y-3">
            <div className="flex justify-between items-start">
              <div>
                <h5 className="text-sm font-bold text-white flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-400" /> {project.title}
                </h5>
                <p className="text-xs text-slate-400 mt-0.5">{project.role}</p>
              </div>
              <span className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full font-semibold">
                Completed
              </span>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-[11px]">
                <span className="text-slate-400">Finalized</span>
                <span className="text-emerald-400 font-mono font-bold">100%</span>
              </div>
              <div className="w-full h-1.5 bg-slate-900 rounded-full overflow-hidden">
                <div className="h-full bg-emerald-500 rounded-full w-full" />
              </div>
            </div>

            <div className="flex items-center justify-between text-xs pt-2 border-t border-slate-900 text-slate-400">
              <span className="text-[11px] text-slate-500">
                Mentored {project.interns ? project.interns.length ?? 0 : 0} Mentees
              </span>

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
  )};