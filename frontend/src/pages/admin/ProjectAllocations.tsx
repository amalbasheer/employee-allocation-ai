import React, { useState, useEffect } from 'react';
import { 
  Plus, Layers, Sliders, Clock, Send, UserCheck, XCircle, CheckCircle2, 
  Tag, Calendar, ArrowRight, ThumbsUp, ThumbsDown, GraduationCap, CheckCircle,
  Star, UserPlus, RefreshCw, Users, FolderPlus, X, PlayCircle, Crown, Sparkles 
} from 'lucide-react';
import { Card } from '../../components/common/Card';
import AIProjectModal from "../../components/AIProjectModal";
import api from '../../services/api'
import { AllocationStatus } from '../../types';

// --- Types ---
export type ProjectStatus = 'open' | 'completed' |'in_progress';
export type AllocatedStatus = 'proposed' | 'accepted' |'rejected' | 'assigned' | 'substituted' | 'unassigned';
export type MainTab = 'ALL_PROJECTS' | 'RECOMMENDATIONS';
export type RecommendationSubTab = 'MENTORS' | 'STUDENTS';

export interface Mentor {
  id: string;
  name: string;
  role: string;
  matchScore: number;
  allocatedHours?: number;
  skills: string[];
}

export interface Student {
  id: string;
  name: string;
  university: string;
  matchScore: number;
  allocatedHours?: number;
  skills: string[];
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
  isSubstituting?: boolean;
}

// --- Mock Data ---
const mockMentors: Mentor[] = [
  { id: 'm-1', name: 'Dr. Sarah Jenkins', role: 'Principal AI Engineer', matchScore: 98, skills: ['PyTorch', 'CUDA', 'FastAPI'] },
  { id: 'm-2', name: 'Alex Morgan', role: 'Staff Systems Architect', matchScore: 91, skills: ['Go', 'Kubernetes', 'AWS'] },
  { id: 'm-3', name: 'Elena Rostova', role: 'Lead Cloud Security Engineer', matchScore: 84, skills: ['Terraform', 'Security', 'Python'] },
  { id: 'm-4', name: 'David Chen', role: 'Senior Backend Engineer', matchScore: 78, skills: ['Java', 'Spring Boot', 'PostgreSQL'] },
];

const mockStudents: Student[] = [
  { id: 's-1', name: 'John Doe', university: 'Stanford University', matchScore: 95, skills: ['Python', 'PyTorch', 'Git'] },
  { id: 's-2', name: 'Maya Patel', university: 'MIT', matchScore: 89, skills: ['FastAPI', 'Docker', 'REST API'] },
  { id: 's-3', name: 'Liam Vance', university: 'UC Berkeley', matchScore: 82, skills: ['Go', 'Kubernetes', 'Linux'] },
  { id: 's-4', name: 'Sophia Kim', university: 'CMU', matchScore: 76, skills: ['React', 'TypeScript', 'Node.js'] },
];


export const ProjectAllocation: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeTab, setActiveTab] = useState<MainTab>('ALL_PROJECTS');
  const [recommendationSubTab, setRecommendationSubTab] = useState<RecommendationSubTab>('MENTORS');
  const [selectedProjectId, setSelectedProjectId] = useState<string|null>(null);
  const [loadingProjects, setLoadingProjects] = useState<boolean>(false);
  // Modal State
  const [isAIModalOpen, setIsAIModalOpen] = useState<boolean>(false);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [projectName, setProjectName] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('Machine Learning');
  const [projectType, setProjectType] = useState('internal_project');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState<string>('');
  const [requiredHours, setRequiredHours] = useState<number>(10);
  const [priorityLevel, setPriorityLevel] = useState<string>('Medium');
  const [skillsInput, setSkillsInput] = useState('');

  const [recommendedMentors, setRecommendedMentors] = useState<Mentor[]>([]);
  const [recommendedStudents, setRecommendedStudents] = useState<Student[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Sync State for Completed Projects
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [syncStatus, setSyncStatus] = useState<string | null>(null);

  const selectedProject = projects.find((p) => p.id === selectedProjectId) || projects[0];

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsModalOpen(false);
    };
    if (isModalOpen) window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isModalOpen]);
   
  const handleAddProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectName.trim()) return;

    try {
    // 1. Prepare backend payload (snake_case)
      const payload = {
        title: projectName.trim(),
        description: description || '',
        category: category || 'General',
        project_type: projectType || 'internal_project',
        start_date: startDate || null,
        end_date: endDate || null,
        required_hours_per_week: Number(requiredHours) || 10,
        priority_level: priorityLevel || 'Medium',
      // Pass raw skills list; AI engine will combine this with description to extract skills
        requirements: skillsInput
          ? skillsInput.split(',').map((s) => s.trim()).filter(Boolean)
          : [],
      };

    // 2. Call FastAPI backend
      const res = await api.post('/api/projects', payload);
      const createdProject = res.data;

    // 3. Map backend response to React state model
      const newProject: Project = {
        id: createdProject.project_id, // Auto-generated ID (e.g., 'rp2-proj-0001')
        name: createdProject.title,
        category: createdProject.category || 'General',
        project_type: createdProject.project_type || 'internal_project',
        status: createdProject.status?.toLowerCase() || 'open',
        description: createdProject.description,
        startDate: createdProject.start_date || 'TBD',
        endDate: createdProject.end_date || 'TBD',
        requiredHoursPerWeek: createdProject.required_hours_per_week,
        priorityLevel: createdProject.priority_level,
      // Map AI-extracted skills if returned by backend, or fallback to user input
        requiredSkills: createdProject.requirements
          ? createdProject.requirements.map((r: any) => r.skill_name || r.skill_id)
          : payload.requirements,
        proposedMentorStatus: 'unassigned',
      };

    // 4. Update UI State
      setProjects([newProject, ...projects]);
      setSelectedProjectId(newProject.id);

    // 5. Reset Form State
      setProjectName('');
      setCategory('Machine Learning');
      setProjectType('internal_project');
      setDescription('');
      setStartDate('');
      setEndDate('');
      setRequiredHours(10);
      setPriorityLevel('Medium');
      setSkillsInput('');
      setIsModalOpen(false);

    } catch (err) {
      console.error('Failed to create project:', err);
      alert('Failed to save project. Please check backend logs.');
    }
  };
  
  const fetchProjects = async () => {
    setLoadingProjects(true);
    try {
      const res = await api.get('/api/projects/details');

    // Map database response (snake_case) to React state model
      const mappedProjects: Project[] = res.data.map((p: any) => {
        const mentorAllocation = p.allocations?.find((a: any) => a.resource_type === 'employee');
        const studentAllocations = p.allocations?.filter((a: any) => a.resource_type === 'intern') || [];

        return {
          id: p.project_id || p.id,
          name: p.title || p.name,
          category: p.category || 'General',
          project_type: p.project_type || 'internal_project',
          status: p.status || 'open',
          requiredSkills: p.skills || p.requiredSkills || [],
          description: p.description,
          startDate: p.start_date || p.startDate || 'TBD',
          proposedMentorId: mentorAllocation?.resource_id || p.proposedMentorId,
          proposedMentorName: mentorAllocation?.resource_name || p.proposedMentorName,
          proposedMentorStatus: mentorAllocation?.allocation_status || 'unassigned',
          allocatedStudentIds: studentAllocations.map((s: any) => s.resource_id) || p.allocatedStudentIds || [],
          allocatedStudentsname: studentAllocations?.map((s: any) => s.resource_name).join(' ,') || p.allocatedStudentsname || [],
        
        };
      });

      setProjects(mappedProjects);
      if (mappedProjects.length > 0 && !selectedProjectId) {
        setSelectedProjectId(mappedProjects[0].id);
      }
    } catch (err) {
      console.error('Failed to fetch projects, loading mock data fallback', err);
    // Fallback mock data if API endpoint is not yet connected or errors out
      const fallbackProjects: Project[] = [
        {
          id: 'p-101',
          name: 'Distributed Database Optimization',
          category: 'Backend Architecture',
          project_type: 'internal_project',
          status: 'open',
          description: 'database related project',
          requiredSkills: ['Go', 'Kubernetes', 'PostgreSQL'],
          startDate: '2026-09-01',
          allocatedStudentIds: [],
          proposedMentorStatus: 'proposed',
        },
        {
          id: 'p-102',
          name: 'AI Recommendation Engine',
          category: 'Machine Learning',
          project_type: 'internal_project',
          status: 'in_progress',
          description: 'AI related project',
          requiredSkills: ['Python', 'PyTorch', 'FastAPI'],
          startDate: '2026-09-15',
          proposedMentorId: 'e1',
          proposedMentorName: 'Dr. Sarah Jenkins',
          allocatedStudentIds: ['s1'],
          proposedMentorStatus: 'assigned',
        },
      ];

      setProjects(fallbackProjects);
      if (fallbackProjects.length > 0 && !selectedProjectId) {
        setSelectedProjectId(fallbackProjects[0].id);
      }
    } finally {
      setLoadingProjects(false);
    }
  };
  
  useEffect(() => {
    if (activeTab === 'ALL_PROJECTS') {
      fetchProjects();
    }
  }, [activeTab]);

  const handleProposeMentor = async (referenceId: string, mentor: Mentor) => {
  // 1. Locate current project in state
  const currentProject = projects.find(
    (p) => p.id === referenceId || p.reference_id === referenceId
  );

  if (!currentProject) {
    console.error("Project not found in state for ID:", referenceId);
    alert("Error: Selected project could not be found.");
    return;
  }

  // 2. Case-insensitive check on all potential status fields
  const rawStatus = String(
    currentProject.proposedMentorStatus ||
    currentProject.status ||
    ''
  ).toLowerCase();

  // Flag as rejected if status contains 'reject' (e.g. 'rejected', 'rejected_by_employee', 'REJECTED')
  const isRejected = rawStatus.includes('reject');

  // Extract allocation ID across all potential keys
  const existingAllocationId =
    currentProject.allocationId ||
    (currentProject.allocationId?.startsWith('rp2-alloc-') ? currentProject.allocationId : null);

  const targetId = existingAllocationId || referenceId;

  console.log("Substitution Check Debug:", {
    referenceId,
    rawStatus,
    isRejected,
    existingAllocationId,
    targetId,
    currentProject
  });

  try {
    let res;

    if (isRejected) {
      console.log("Calling SUBSTITUTE endpoint for allocation:", existingAllocationId);
      
      // --- SUBSTITUTE API CALL ---
      const substitutePayload = {
        substitute_resource_type: 'employee',
        substitute_resource_id: mentor.id,
        reason: 'Re-proposing replacement mentor after employee rejection',
      };

      res = await api.post(
        `api/allocations/${targetId}/substitute`,
        substitutePayload
      );
    } else {
      console.log("Calling PROPOSE endpoint for reference:", referenceId);
      
      // --- STANDARD PROPOSE API CALL ---
      const proposePayload = {
        reference_id: referenceId,
        reference_type: 'project',
        resource_type: 'employee',
        resource_id: mentor.id,
        role_on_project: mentor.role || 'Project Mentor',
        allocated_hours: mentor.allocatedHours || 10,
        suitability_score: mentor.matchScore || 0.85,
      };

      res = await api.post('api/allocations/propose', proposePayload);
    }

    const data = res.data;

    // 3. Update local state back to 'proposed' for the new mentor
    setProjects((prev) =>
      prev.map((p) =>
        p.id === referenceId || p.reference_id === referenceId
          ? {
              ...p,
              proposedMentorStatus: 'proposed',
              allocationStatus: 'proposed',
              proposedMentorId: mentor.id,
              proposedMentorName: mentor.name,
              allocationId: data.allocation_id || data.new_allocation_id || existingAllocationId,
            }
          : p
      )
    );

    alert(isRejected ? 'Mentor substituted successfully!' : 'Mentor proposed successfully!');
  } catch (err: any) {
    const errorMsg = err.response?.data?.detail || 'Failed to assign mentor.';
    console.error('Error handling mentor assignment:', errorMsg);
    alert(`Action Failed: ${errorMsg}`);
  }
};

  // 1. Accept or Reject Proposal (Simulating Mentor Response)
  const handleSimulateMentorResponse = async (
    allocationId: string, 
    response: 'ACCEPT' | 'REJECT'
  ) => {
    try {
      const targetStatus = response === 'ACCEPT' ? 'accepted' : 'rejected';
      const res = await api.patch(`/allocations/${allocationId}/status`, {
        status: targetStatus,
        reason: `Mentor ${response.toLowerCase()}ed project proposal.`
      });

    // Update local state after successful backend response
      setProjects((prev) =>
        prev.map((p) => p.allocationId === allocationId ? { ...p, proposedMentorStatus: targetStatus } : p)
      );
    } catch (err) {
      console.error("Failed to update mentor response:", err);
    }
  };

// 2. Confirm Mentor Assignment (Admin Action)
  // Confirm Mentor Assignment (Admin Action)
  // Confirm Mentor Assignment (Admin Action)
  const handleConfirmMentor = async (
    itemOrId: string | { allocationId?: string; reference_id?: string; project_id?: string; id?: string }
  ) => {
  // 1. Resolve target identifier (supports string directly or extracts from object)
    const targetId = typeof itemOrId === 'string'
      ? itemOrId
      : itemOrId.allocationId || itemOrId.reference_id || itemOrId.project_id || itemOrId.id;

    if (!targetId) {
      console.error("Cannot confirm assignment: Missing target ID.", itemOrId);
      alert("Error: Missing allocation or project identifier.");
      return;
    }

    try {
    // 2. Call backend PATCH endpoint (backend handles reference_id or allocation_id)
      const res = await api.patch(`api/allocations/${targetId}/assign`, {
        status: 'assigned'
      });

      if (res.data) {
      // 3. Update local UI state
        setProjects((prevProjects) =>
          prevProjects.map((p) =>
            p.id === targetId ||
            p.allocationId === targetId ||
            p.reference_id === targetId
              ? {
                  ...p,
                  status: 'in_progress',
                  allocationStatus: 'assigned',
                  proposedMentorStatus: 'assigned', // Updates UI from 'accepted' to 'assigned'
                  isSubstituting: false            // Resets substitution tracking state
                }
              : p
          )
        );
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || "Failed to confirm mentor assignment.";
      console.error("Confirmation error:", errorMsg);
      alert(`Action Failed: ${errorMsg}`);
    }
  };

// 3. Reset or Cancel Proposal (Admin Action)
  const handleResetMentorProposal = async (allocationId: string) => {
    try {
      const res = await api.patch(`api/allocations/${allocationId}/status`, {
        status: 'cancelled',
        reason: 'Admin reset the mentor proposal.'
      });

      setProjects((prev) =>
        prev.map((p) =>
          p.allocationId === allocationId
            ? { ...p, status: 'open', proposedMentorId: undefined, proposedMentorName: undefined }
            : p
        )
      );
    } catch (err) {
      console.error("Failed to reset mentor proposal:", err);
    }
  };

  const handleAssignStudent = async (referenceId: string, studentId: string, studentData?: any) => {
  // 1. Locate current project in state
    const currentProject = projects.find(
      (p) => p.id === referenceId || p.reference_id === referenceId
    );

    if (!currentProject) {
      console.error("Project not found in state for ID:", referenceId);
      alert("Error: Selected project could not be found.");
      return;
    }

    const allocatedStudentIds = currentProject.allocatedStudentIds ?? [];
    const isAssigned = allocatedStudentIds.includes(studentId);

    try {
      if (isAssigned) {
      // --- REMOVE / UNASSIGN INTERN ---
      // Optional: Call remove endpoint if present, e.g. await api.delete(`api/allocations/student/${referenceId}/${studentId}`);
      
        setProjects((prev) =>
          prev.map((p) => {
            if (p.id === referenceId || p.reference_id === referenceId) {
              return {
                ...p,
                allocatedStudentIds: (p.allocatedStudentIds ?? []).filter((id) => id !== studentId),
              };
            }
            return p;
          })
        );
      } else {
      // --- ASSIGN INTERN VIA API ---
        const assignPayload = {
          reference_id: referenceId,
          resource_id: studentId,
          reference_type: 'project',
          resource_type: 'intern',
          role_on_project: studentData?.role || 'Student Contributor',
          allocated_hours: studentData?.recommendedHours || 10,
          suitability_score: (studentData?.matchScore || 85) / 100, // Converts percentage to decimal
        };

        const res = await api.post('api/allocations/assign-student', assignPayload);

      // Update local state with newly assigned student ID
        setProjects((prev) =>
          prev.map((p) => {
            if (p.id === referenceId || p.reference_id === referenceId) {
              const currentIds = p.allocatedStudentIds ?? [];
              return {
                ...p,
                allocatedStudentIds: [...currentIds, studentId],
              };
            }
            return p;
          })
        );

        alert('Student assigned successfully!');
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to update student allocation.';
      console.error('Error handling student allocation:', errorMsg);
      alert(`Action Failed: ${errorMsg}`);
    }
  };

  const handleManageAllocation = (projectId: string, initialSubTab: RecommendationSubTab = 'MENTORS') => {
    setSelectedProjectId(projectId);
    setRecommendationSubTab(initialSubTab);
    setActiveTab('RECOMMENDATIONS');
  };

  const renderStatusBadge = (
    ProjectStatus?: string,
    AllocatedStatus?: string
  ) => {
    const pStatus = ProjectStatus;
    const aStatus = AllocatedStatus;

  // 1. Prioritize direct project status (In Progress / Completed)
    if (pStatus === 'in_progress') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <PlayCircle className="w-3 h-3" /> In Progress
        </span>
      );
    }

    if (pStatus === 'completed') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <CheckCircle className="w-3 h-3" /> Completed
        </span>
      );
    }

  // 2. If Project Status is 'OPEN', check Allocation Status
    if (pStatus === 'open' || !pStatus) {
      switch (aStatus) {
        case 'proposed':
        case 'pending':
          return (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <Send className="w-3 h-3" /> Proposal Sent
            </span>
          );

        case 'accepted':
        case 'approved':
          return (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
              <UserCheck className="w-3 h-3" /> Mentor Accepted
            </span>
          );

        case 'rejected':
        case 'declined':
          return (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
              <XCircle className="w-3 h-3" /> Mentor Declined (Unassigned)
            </span>
          );
        case 'substituted':
          return (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-purple-500/10 text-purple-400 border border-purple-500/20">
              <RefreshCw className="w-3 h-3" /> Mentor Substituted
            </span>
          );
        
        case 'unassigned':
        default:
          return (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <Clock className="w-3 h-3" /> Unassigned
            </span>
          );
      }
    }
    
  // Fallback for unhandled statuses
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-500/10 text-slate-400 border border-slate-500/20">
        <Clock className="w-3 h-3" /> {AllocatedStatus}
      </span>
    );
  };
  
  // --- NEW: SYNC COMPLETED PROJECTS HANDLER ---
  const handleSyncCompletedProjects = async () => {
    setIsSyncing(true);
    setSyncStatus(null);

    try {
      const res = await api.post('api/admin/sync-completed-projects');

      if (res.data && res.data.success) {
        const syncedCount = res.data.count ?? res.data.synced_count ?? 0;
        setSyncStatus(`Synced ${syncedCount} records`);
        
        // Re-fetch projects to refresh dashboard data
        fetchProjects();
      } else {
        setSyncStatus('Sync failed');
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.response?.data?.error || 'Failed to sync completed projects.';
      console.error('Error syncing completed projects:', errorMsg);
      setSyncStatus('Sync failed');
      alert(`Sync Failed: ${errorMsg}`);
    } finally {
      setIsSyncing(false);
    }
  };

  const getAssignedStudentNames = (studentIds: string[]) => {
    return studentIds
      .map((id) => mockStudents.find((s) => s.id === id)?.name)
      .filter(Boolean)
      .join(', ');
  };

  // Fetch data when active project or sub-tab changes
  const fetchSubTabRecommendations = async (projectId: string, subTab: 'MENTORS' | 'STUDENTS') => {
    if (!projectId) return;
    setIsLoading(true);

    try {
    // Map 'MENTORS' subtab to fetch 'team_leads' from backend
      const apiType = subTab === 'MENTORS' ? 'team_leads' : 'students';

      const res = await api.post(`/api/projects/${projectId}/recommendations`, {
        type: apiType,
      });

      if (subTab === 'MENTORS') {
        setRecommendedMentors(res.data); // Stores only team leads for mentors
      } else {
        setRecommendedStudents(res.data);
      }
    } catch (err) {
      console.error(`Failed to fetch ${subTab} recommendations:`, err);
    } finally {
      setIsLoading(false);
    }
  };

// Trigger fetch on tab or project change
  useEffect(() => {
    if (selectedProjectId && activeTab === 'RECOMMENDATIONS') {
      fetchSubTabRecommendations(selectedProjectId, recommendationSubTab);
    }
  }, [selectedProjectId, activeTab, recommendationSubTab]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white">Project Allocation Portal</h1>
          <p className="text-slate-400 text-sm">Manage projects and assign recommended mentors and students.</p>
        </div>
        <div className="flex items-center gap-3">
  {/* Standard Add Project Button */}
  <button
    onClick={() => setIsModalOpen(true)}
    className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-2.5 rounded-xl flex items-center gap-2 shadow-lg transition-all"
    type="button"
  >
    <Plus className="w-4 h-4" /> Add Project
  </button>
  {/* Sync Completed Projects Refresh Button */}
        <button
          onClick={handleSyncCompletedProjects}
          disabled={isSyncing}
          className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-semibold px-4 py-2.5 rounded-xl flex items-center gap-2 shadow-lg transition-all"
          type="button"
        >
          <RefreshCw className={`w-4 h-4 ${isSyncing ? "animate-spin" : ""}`} />
          {isSyncing ? "Syncing..." : "Sync Completed Projects"}
        </button>
  {/* AI Project Generator Button */}
  <button
    onClick={() => setIsAIModalOpen(true)}
    className="bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold px-4 py-2.5 rounded-xl flex items-center gap-2 shadow-lg transition-all"
    type="button"
  >
    <Sparkles size={16} /> Generate AI Project
  </button>
</div>
      
      </div>

      {/* Main Navigation Tabs */}
      <div className="flex border-b border-slate-800 gap-6">
        <button
          onClick={() => setActiveTab('ALL_PROJECTS')}
          className={`pb-3 text-sm font-medium flex items-center gap-2 border-b-2 transition-all ${
            activeTab === 'ALL_PROJECTS'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Layers className="w-4 h-4" /> All Projects ({loadingProjects ? '...': projects.length})
        </button>
        <button
          onClick={() => setActiveTab('RECOMMENDATIONS')}
          className={`pb-3 text-sm font-medium flex items-center gap-2 border-b-2 transition-all ${
            activeTab === 'RECOMMENDATIONS'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Sliders className="w-4 h-4" /> Resource Allocation
        </button>
      </div>

      {/* TAB 1: ALL PROJECTS LIST */}
      {activeTab === 'ALL_PROJECTS' && (
        <Card title="Project Directory">
          {loadingProjects ? (
            <div className="p-8 text-center text-slate-400 flex justify-center items-center gap-2">
              <span className="animate-spin rounded-full h-5 w-5 border-b-2 border-indigo-500"></span>
                Loading projects...
            </div>
          ) : projects.length === 0 ? (
            <div className="p-8 text-center text-slate-400">No projects available. Create one to get started.</div>
          ) : (
            <div className="space-y-4">
              {projects.map((project) => (
                <div
                  key={project.id}
                  className="p-5 bg-slate-950 border border-slate-800 rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-4 transition-all hover:border-slate-700"
                >
                  <div className="space-y-2">
                    <div className="flex items-center gap-3">
                      <h4 className="font-bold text-white text-base">{project.name}</h4>
                      {renderStatusBadge(project.status, project.proposedMentorStatus)}
                    </div>

                    <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400">
                      <span className="flex items-center gap-1 text-slate-300">
                        <Tag className="w-3.5 h-3.5 text-indigo-400" /> {project.category}
                      </span>
                      <span className="flex items-center gap-1 text-slate-300">
                        <Tag className="w-3.5 h-3.5 text-indigo-400" /> {project.project_type}
                      </span>
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5" /> Start: {project.startDate}
                      </span>
                    </div>
                    
                    <div className="flex flex-wrap gap-1.5 pt-1">
  {(project.requiredSkills ?? []).map((skill, index) => (
    <span key={index} className="text-[11px] bg-slate-900 text-slate-300 px-2 py-0.5 rounded-md border border-slate-800">
      {typeof skill === 'object' && skill !== null
        ? ((skill as { skill_name?: string; skill_id?: string }).skill_name ||
          (skill as { skill_name?: string; skill_id?: string }).skill_id)
        : skill}
    </span>
  ))}
</div>
                  </div>

                  <div className="flex flex-col md:items-end gap-3 border-t md:border-t-0 border-slate-800 pt-3 md:pt-0">
                    <div className="text-xs text-slate-400 space-y-1 md:text-right">
                      <div>
                        Mentor:{' '}
                        {project.proposedMentorName ? (
                          <strong className="text-slate-200">{project.proposedMentorName}</strong>
                        ) : (
                          <span className="text-amber-400/80 italic">Unassigned</span>
                        )}
                      </div>
                      <div>
                        Students ({(project.allocatedStudentIds ?? []).length}):{' '}
                        {project.allocatedStudentsname ? (
                          <strong className="text-slate-200">{project.allocatedStudentsname}</strong>
                        ) : (
                          <span className="text-slate-500">Unassigned</span>
                        )}
                      </div>
                    </div>

                    <button
                      onClick={() => handleManageAllocation(project.id)}
                      className="bg-slate-900 hover:bg-slate-800 text-slate-200 text-xs font-semibold px-3 py-1.5 rounded-lg border border-slate-700 flex items-center gap-1.5 transition-all self-start md:self-end"
                    >
                      Manage Allocation <ArrowRight className="w-3.5 h-3.5 text-indigo-400" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* TAB 2: RECOMMENDATIONS & ALLOCATION */}
      {activeTab === 'RECOMMENDATIONS' && (
        <Card title="Resource Recommendation Portal">
          {!selectedProject ? (
            <div className="p-8 text-center text-slate-400">No project selected.</div>
          ) : (
            <div className="space-y-6">
              {/* Project Selector Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 bg-slate-900 border border-slate-800 rounded-xl">
                <div>
                  <label htmlFor="project-select" className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                    Select Target Project
                  </label>
                  <select
                    id="project-select"
                    value={selectedProject.id}
                    onChange={(e) => setSelectedProjectId(e.target.value)}
                    className="bg-slate-950 text-white text-sm font-semibold rounded-lg border border-slate-700 px-3 py-2 focus:outline-none focus:border-indigo-500"
                  >
                    {projects.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} ({p.project_type})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400">
                  <div>
                    Mentor:{' '}
                    <span className="font-semibold text-slate-200">
                      {selectedProject.proposedMentorName || <span className="text-amber-400/80 italic">Unassigned</span>}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span>Status:</span>
                    {renderStatusBadge(selectedProject.status, selectedProject.proposedMentorStatus)}
                  </div>
                </div>
              </div>

              {/* SIMULATED EMPLOYEE DASHBOARD ACTION BANNER */}
              {selectedProject.proposedMentorStatus === 'proposed' && (
                <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl flex items-center justify-between">
                  <div>
                    <p className="text-sm font-bold text-amber-300">Employee Dashboard Simulation</p>
                    <p className="text-xs text-slate-400">Project proposed to {selectedProject.proposedMentorName}. Simulate employee decision:</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleSimulateMentorResponse(selectedProject.id, 'ACCEPT')}
                      className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold px-3 py-1.5 rounded-lg flex items-center gap-1 transition-all"
                    >
                      <ThumbsUp className="w-3.5 h-3.5" /> Employee Accept
                    </button>
                    <button
                      onClick={() => handleSimulateMentorResponse(selectedProject.id, 'REJECT')}
                      className="bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold px-3 py-1.5 rounded-lg flex items-center gap-1 transition-all"
                    >
                      <ThumbsDown className="w-3.5 h-3.5" /> Employee Reject
                    </button>
                  </div>
                </div>
              )}

              {/* Sub-Tabs */}
              <div className="flex border-b border-slate-800 gap-4 pt-2">
                <button
                  onClick={() => setRecommendationSubTab('MENTORS')}
                  className={`pb-2 text-xs font-bold uppercase tracking-wider flex items-center gap-2 border-b-2 transition-all ${
                    recommendationSubTab === 'MENTORS'
                      ? 'border-indigo-500 text-indigo-400'
                      : 'border-transparent text-slate-500 hover:text-slate-300'
                  }`}
                >
                  <UserCheck className="w-4 h-4" /> Recommended Mentors
                </button>
                <button
                  onClick={() => setRecommendationSubTab('STUDENTS')}
                  className={`pb-2 text-xs font-bold uppercase tracking-wider flex items-center gap-2 border-b-2 transition-all ${
                    recommendationSubTab === 'STUDENTS'
                      ? 'border-indigo-500 text-indigo-400'
                      : 'border-transparent text-slate-500 hover:text-slate-300'
                  }`}
                >
                  <GraduationCap className="w-4 h-4" /> Recommended Interns
                </button>
              </div>

              {/* MENTOR RECOMMENDATIONS */}
              {recommendationSubTab === 'MENTORS' && (
                <div className="space-y-3">
                  <p className="text-xs text-slate-400">
                    Top mentors matching skills ({selectedProject.requiredSkills?.join(', ') || 'None specified'}).
                  </p>

                  <div className="grid grid-cols-1 gap-4 pt-2">
                    {recommendedMentors.map((mentor, idx) => {
                      const isThisMentorProposed = selectedProject.proposedMentorId === mentor.id;
                      const hasAnyMentorProposed = Boolean(selectedProject.proposedMentorId);
                      const isRejected = selectedProject.proposedMentorStatus === 'rejected';
                      const isTopMentor = idx === 0;

                      return (
                        <div
                          key={mentor.id}
                          className={`relative bg-slate-950 border rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-4 transition-all ${
                            isTopMentor ? 'pt-7 pb-4 px-5 border-[#c59b27]/40' : 'p-5 border-slate-800'
                          } ${isThisMentorProposed ? 'border-indigo-500/50 bg-indigo-950/10' : ''}`}
                        >
                          {/* MATTE METALLIC GOLD OVERFLOWING CORNER BADGE ONLY */}
                          {isTopMentor && (
                            <div className="absolute -top-px -left-px bg-[#c59b27] text-slate-950 text-[10px] font-bold tracking-wide px-3 py-1 rounded-tl-xl rounded-br-lg border-b border-r border-[#d4af37] flex items-center gap-1.5">
                              <Crown className="w-3 h-3 text-slate-950 fill-slate-950" />
                              Top Best Mentor Matched
                            </div>
                          )}

                          <div className="space-y-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <h5 className="font-bold text-white text-sm">{mentor.name}</h5>
                              <span className="text-[10px] bg-emerald-500/10 text-emerald-400 font-mono px-2 py-0.5 rounded border border-emerald-500/20 flex items-center gap-1">
                                <Star className="w-3 h-3 fill-emerald-400" /> {mentor.matchScore}% Match
                              </span>
                            </div>
                            <p className="text-xs text-slate-400">{mentor.role}</p>

                            <div className="flex flex-wrap gap-1 pt-1">
                              {mentor.skills.map((skill, i) => (
                                <span key={i} className="text-[10px] bg-slate-900 text-slate-400 px-2 py-0.5 rounded border border-slate-800">
                                  {skill}
                                </span>
                              ))}
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                          {/* 1. Proposed State: Waiting for Mentor Acceptance */}
                          {isThisMentorProposed && selectedProject.proposedMentorStatus === 'proposed' && (
                            <div className="flex flex-col items-end gap-1">
                              <button
                                disabled
                                className="bg-slate-800 text-slate-400 cursor-not-allowed text-xs font-semibold px-4 py-2 rounded-lg flex items-center gap-1.5 border border-slate-700 opacity-80"
                              >
                                <Send className="w-3.5 h-3.5 text-amber-400" /> Proposed
                              </button>
                              <span className="text-[10px] text-amber-400 font-medium italic">
                                Waiting for acceptance...
                              </span>
                            </div>
                          )}

                          {/* 2. Accepted State: Confirm Button (Handles Initial Allocation vs. Substitution) */}
                          {isThisMentorProposed && selectedProject.proposedMentorStatus === 'accepted' && (
                            <div className="flex flex-col items-end gap-1">
                              <button
                                onClick={() => handleConfirmMentor(selectedProject.id)}
                                className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold px-4 py-2 rounded-lg transition-all shadow-lg animate-pulse flex items-center gap-1.5"
                              >
                                <CheckCircle2 className="w-3.5 h-3.5" />
                                {selectedProject.isSubstituting || selectedProject.status === 'open'
                                  ? 'Confirm Substitution'
                                  : 'Confirm Allocation'}
                              </button>
                              <span className="text-[10px] text-emerald-400 font-medium">
                                {selectedProject.isSubstituting || selectedProject.status === 'open'
                                  ? 'Substituted mentor accepted proposal!'
                                  : 'Mentor accepted proposal!'}
                                </span>
                              </div>
                            )}

                            {/* 3. Assigned State: Active Mentor */}
                            {isThisMentorProposed && selectedProject.proposedMentorStatus === 'assigned' && (
                              <div className="flex items-center gap-2">
                                <span className="text-xs text-emerald-400 font-bold flex items-center gap-1.5 bg-emerald-500/10 px-3 py-1.5 rounded-lg border border-emerald-500/20">
                                  <CheckCircle2 className="w-3.5 h-3.5" /> Assigned Mentor
                                </span>
                                <button
                                  onClick={() => handleResetMentorProposal(selectedProject.id)}
                                  className="text-xs text-slate-400 hover:text-rose-400 p-1.5 rounded-lg hover:bg-slate-800 transition-all flex items-center gap-1"
                                  title="Substitute Mentor"
                                >
                                  <RefreshCw className="w-3.5 h-3.5" /> Substitute
                                </button>
                              </div>
                            )}

                            {/* 4. Unproposed State: Propose / Substitute Action */}
                            {!isThisMentorProposed && (
                              <button
                                onClick={() => handleProposeMentor(selectedProject.id, mentor)}
                                disabled={
                                  hasAnyMentorProposed &&
                                  !['rejected', 'reset'].includes(selectedProject.proposedMentorStatus ?? '')
                                }
                                className={`text-xs font-semibold px-4 py-2 rounded-lg flex items-center gap-1.5 transition-all ${
                                  hasAnyMentorProposed &&
                                  !['rejected', 'reset'].includes(selectedProject.proposedMentorStatus ?? '')
                                    ? 'bg-slate-800/60 text-slate-500 border border-slate-800 cursor-not-allowed'
                                    : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-md'
                                }`}
                                title={
                                  hasAnyMentorProposed &&
                                  !['rejected', 'reset'].includes(selectedProject.proposedMentorStatus ?? '')
                                    ? 'Another mentor is already proposed or assigned'
                                    : ['rejected', 'reset'].includes(selectedProject.proposedMentorStatus ?? '')
                                      ? 'Propose as substituted mentor'
                                      : 'Propose this mentor'
                                }
                              >
                                <UserPlus className="w-3.5 h-3.5" />
                                {['rejected', 'reset'].includes(selectedProject.proposedMentorStatus  ?? '')
                                  ? 'Substitute Mentor'
                                  : 'Propose as Mentor'}
                              </button>
                            )}
                            {/* 1. Proposed State: Waiting for Mentor Acceptance */}
                          {isThisMentorProposed && selectedProject.proposedMentorStatus === 'substituted' && (
                            <div className="flex flex-col items-end gap-1">
                              <button
                                disabled
                                className="bg-slate-800 text-slate-400 cursor-not-allowed text-xs font-semibold px-4 py-2 rounded-lg flex items-center gap-1.5 border border-slate-700 opacity-80"
                              >
                                <Send className="w-3.5 h-3.5 text-amber-400" /> Substituted
                              </button>
                              <span className="text-[10px] text-amber-400 font-medium italic">
                                Waiting for acceptance...
                              </span>
                            </div>
                          )}
                            {/* 2. Accepted State: Confirm Button (Handles Initial Allocation vs. Substitution) */}
                          {isThisMentorProposed && selectedProject.proposedMentorStatus === 'accepted' && (
                            <div className="flex flex-col items-end gap-1">
                              <button
                                onClick={() => handleConfirmMentor(selectedProject.id)}
                                className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold px-4 py-2 rounded-lg transition-all shadow-lg animate-pulse flex items-center gap-1.5"
                              >
                                <CheckCircle2 className="w-3.5 h-3.5" />
                                {selectedProject.isSubstituting || selectedProject.status === 'open'
                                  ? 'Confirm Substitution'
                                  : 'Confirm Allocation'}
                              </button>
                              <span className="text-[10px] text-emerald-400 font-medium">
                                {selectedProject.isSubstituting || selectedProject.status === 'open'
                                  ? 'Substituted mentor accepted proposal!'
                                  : 'Mentor accepted proposal!'}
                                </span>
                              </div>
                            )}

                        </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* STUDENT RECOMMENDATIONS */}
              {recommendationSubTab === 'STUDENTS' && (
                <div className="space-y-3">
                  <p className="text-xs text-slate-400">
                    Top recommended interns matching skills.
                  </p>

                  <div className="grid grid-cols-1 gap-4 pt-2">
                    {recommendedStudents.map((student, idx) => {
                      const isAssigned = (selectedProject.allocatedStudentIds ?? []).includes(student.id);
                      const isTopStudent = idx === 0;

                      return (
                        <div
                          key={student.id}
                          className={`relative bg-slate-950 border rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-4 transition-all ${
                            isTopStudent ? 'pt-7 pb-4 px-5 border-[#c59b27]/40' : 'p-5 border-slate-800'
                          } ${isAssigned ? 'border-blue-500/50 bg-blue-950/10' : ''}`}
                        >
                          {/* MATTE METALLIC GOLD OVERFLOWING CORNER BADGE ONLY */}
                          {isTopStudent && (
                            <div className="absolute -top-px -left-px bg-[#c59b27] text-slate-950 text-[10px] font-bold tracking-wide px-3 py-1 rounded-tl-xl rounded-br-lg border-b border-r border-[#d4af37] flex items-center gap-1.5">
                              <Crown className="w-3 h-3 text-slate-950 fill-slate-950" />
                              Top Best Intern Matched
                            </div>
                          )}

                          <div className="space-y-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <h5 className="font-bold text-white text-sm">{student.name}</h5>
                              <span className="text-[10px] bg-emerald-500/10 text-emerald-400 font-mono px-2 py-0.5 rounded border border-emerald-500/20 flex items-center gap-1">
                                <Star className="w-3 h-3 fill-emerald-400" /> {student.matchScore}% Match
                              </span>
                            </div>
                            <p className="text-xs text-slate-400">{student.university}</p>

                            <div className="flex flex-wrap gap-1 pt-1">
                              {student.skills.map((skill, i) => (
                                <span key={i} className="text-[10px] bg-slate-900 text-slate-400 px-2 py-0.5 rounded border border-slate-800">
                                  {skill}
                                </span>
                              ))}
                            </div>
                          </div>

                          <div>
                            <button
                              onClick={() => handleAssignStudent(selectedProject.id, student.id, student)}
                              className={`text-xs font-semibold px-4 py-2 rounded-lg flex items-center gap-1.5 transition-all ${
                                isAssigned
                                  ? 'bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 border border-rose-500/30'
                                  : 'bg-blue-600 hover:bg-blue-500 text-white'
                              }`}
                            >
                              {isAssigned ? (
                                <>Remove Intern</>
                              ) : (
                                <><Users className="w-3.5 h-3.5" /> Assign Intern</>
                              )}
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}
        </Card>
      )}

      {/* ADD PROJECT MODAL */}
      {isModalOpen && (
        <div 
          className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={() => setIsModalOpen(false)}
        >
          <div 
            className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 space-y-5 shadow-2xl max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
          >
            <div className="flex justify-between items-center border-b border-slate-800 pb-4">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <FolderPlus className="w-5 h-5 text-indigo-400" /> Create New Project
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-all"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAddProject} className="space-y-4">
              {/* Project Title */}
              <div>
                <label htmlFor="modal-project-title" className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Project Title *
                </label>
                <input
                  id="modal-project-title"
                  type="text"
                  required
                  placeholder="e.g. Distributed Database Optimization"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              {/* Category & Priority */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="modal-category" className="block text-xs font-semibold text-slate-300 mb-1.5">
                    Category
                  </label>
                  <select
                    id="modal-category"
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="Machine Learning">Machine Learning</option>
                    <option value="DevOps & Security">DevOps & Security</option>
                    <option value="Full Stack">Full Stack</option>
                    <option value="Backend Architecture">Backend Architecture</option>
                    <option value="Backend Architecture">Data Science</option>
                    <option value="Backend Architecture">Data Analytics</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="modal-project-type" className="block text-xs font-semibold text-slate-300 mb-1.5">
                    Project Type
                  </label>
                  <select
                    id="modal-project-type"
                    value={projectType}
                    onChange={(e) => setProjectType(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="internal_project">internal_project</option>
                  </select>
                </div>
              </div>

              {/* Start Date & End Date */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="modal-start-date" className="block text-xs font-semibold text-slate-300 mb-1.5">
                    Start Date
                  </label>
                  <input
                    id="modal-start-date"
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label htmlFor="modal-end-date" className="block text-xs font-semibold text-slate-300 mb-1.5">
                    End Date
                  </label>
                  <input
                    id="modal-end-date"
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              {/* Required Hours Per Week */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="modal-hours" className="block text-xs font-semibold text-slate-300 mb-1.5">
                    Required Hours / Week
                  </label>
                  <input
                    id="modal-hours"
                    type="number"
                    min="1"
                    max="168"
                    placeholder="e.g. 10"
                    value={requiredHours}
                    onChange={(e) => setRequiredHours(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
                
                <div>
                  <label htmlFor="modal-priority" className="block text-xs font-semibold text-slate-300 mb-1.5">
                    Priority Level
                  </label>
                  <select
                    id="modal-priority"
                    value={priorityLevel}
                    onChange={(e) => setPriorityLevel(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="Low">Low</option>
                    <option value="Medium">Medium</option>
                    <option value="High">High</option>
                    <option value="Critical">Critical</option>
                  </select>
                </div>
              </div>

              {/* Description Section */}
              <div>
                <label htmlFor="modal-description" className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Description
                </label>
                <textarea
                  id="modal-description"
                  rows={4}
                  placeholder="Describe project details, objectives, and required technical skill sets..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 resize-none"
                />
              </div>

               {/* Action Buttons */}
              <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-all shadow-md"
               >
                  Create Project
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      {/* 4. Render the AI Modal */}
      <AIProjectModal
        isOpen={isAIModalOpen}
        onClose={() => setIsAIModalOpen(false)}
      />
    </div>
  );}
  // Inline TypeScript style definitions
const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: "24px",
    color: "var(--text-main, currentColor)",
  },
  headerRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "24px",
  },
  title: {
    fontSize: "24px",
    fontWeight: 700,
    margin: 0,
    color: "var(--text-main, currentColor)",
  },
  subtitle: {
    fontSize: "14px",
    color: "var(--text-muted, #64748b)",
    margin: "4px 0 0 0",
  },
  aiButton: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    padding: "10px 18px",
    backgroundColor: "#8b5cf6",
    color: "#ffffff",
    border: "none",
    borderRadius: "6px",
    fontWeight: 600,
    cursor: "pointer",
    transition: "background-color 0.2s ease",
  },
}
;