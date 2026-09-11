import React, { useState, useEffect, useMemo } from 'react';
import { Card } from '../../components/common/Card';
import { 
  Video, Plus, Clock, CheckCircle2, XCircle, Send, 
  UserCheck, Star, UserPlus, Sliders, ArrowRight, Download, FolderSync, Hourglass,
  GraduationCap, RefreshCw, Sparkles, Filter, AlertCircle, X, Loader2, Crown, Users
} from 'lucide-react';

export type EngagementTypeFilter = 'all' | 'webinar' | 'demo' | 'workshop' | 'seminar';
export type EngagementStatus = 'open' | 'proposed' | 'accepted' | 'rejected' | 'allocated' | 'completed';

export interface WebinarIdea {
  id: string | number;
  title: string;
  summary: string;
  format_type: string;
  duration_hours: number;
  target_audience: string;
  key_takeaways?: string[];
}

export interface RecommendedMentor {
  employee_id: string;
  id?: string;
  name: string;
  designation: string;
  match_score: number;
  skills?: string[];
  is_team_lead?: boolean;
  batch_count?: number;
}

export interface TrainingEngagement {
  engagement_id: string;
  title: string;
  engagement_type: 'webinar' | 'demo' | 'workshop' | 'seminar';
  description?: string;
  start_date: string;
  end_date?: string;
  required_hours: number;
  mentor_id?: string;
  mentor_name?: string;
  audience?: string;
  region?: string;
  institution_name?: string;
  mode?: string;
  domain?: string;
  status: EngagementStatus;
  created_at?: string;
  location: string;
}

export interface StudentBatch {
  batch_id: string;
  batch_name: string;
  domain: string;
  start_date: string;
  end_date: string;
  trainer_ids?: string;
  trainer_name?: string;
  status: string;
  delivery_mode?: string;
}

export interface TrainingAssignment {
  engagement_id: string;
  candidate_id: string;
  candidate_name: string;
  score: number;
  candidate_skills: string[];
}

export interface TrainingOptimizeResponse {
  assignments: TrainingAssignment[];
  unstaffed_engagements: string[];
}

// Fallback Data (Used only if API calls fail)
const fallbackMentors: RecommendedMentor[] = [
  {
    employee_id: 'emp-101',
    name: 'Dr. Sarah Jenkins',
    designation: 'Principal AI Engineer',
    match_score: 98,
    skills: ['PyTorch', 'CUDA', 'Deep Learning']
  },
  {
    employee_id: 'emp-102',
    name: 'Alex Morgan',
    designation: 'Staff Systems Architect',
    match_score: 92,
    skills: ['Distributed Systems', 'Go', 'Kubernetes']
  },
  {
    employee_id: 'emp-103',
    name: 'Elena Rostova',
    designation: 'Lead Cloud Security Developer',
    match_score: 86,
    skills: ['AWS', 'Zero Trust', 'Python']
  }
];

const fallbackBatches: StudentBatch[] = [
  {
    batch_id: 'rp2-batch-0001',
    batch_name: 'Batch-Jun-Jul-2026',
    domain: 'Data Analytics',
    start_date: '2026-06-15',
    end_date: '2026-07-15',
    trainer_ids: 'emp-101',
    trainer_name: 'Dr. Sarah Jenkins',
    status: 'open',
    delivery_mode: 'online'
  },
  {
    batch_id: 'rp2-batch-0002',
    batch_name: 'Batch-Jul-Aug-2026',
    domain: 'Data Science',
    start_date: '2026-07-15',
    end_date: '2026-08-15',
    trainer_ids: 'emp-102',
    trainer_name: 'Alex Morgan',
    status: 'open',
    delivery_mode: 'hybrid'
  }
];

const fallbackEngagements: TrainingEngagement[] = [
  {
    engagement_id: 'rp2-train-0001',
    title: 'Advanced Neural Networks & PyTorch',
    engagement_type: 'workshop',
    description: 'Deep dive into model optimization and GPU acceleration.',
    start_date: '2026-09-10',
    end_date: '2026-09-12',
    required_hours: 8,
    status: 'open',
    location: 'Building B - Auditorium',
    domain: 'AI & Data'
  }
];

export const TrainingManagement: React.FC = () => {
  const [mainTab, setMainTab] = useState<'engagements' | 'student_batch'>('engagements');
  const [typeFilter, setTypeFilter] = useState<EngagementTypeFilter>('all');
  const [subTab, setSubTab] = useState<'list' | 'allocation' | 'optimizations'>('list');

  // Real Data States
  const [engagements, setEngagements] = useState<TrainingEngagement[]>([]);
  const [batches, setBatches] = useState<StudentBatch[]>([]);
  const [selectedEngagementId, setSelectedEngagementId] = useState<string>('');
  const [recommendedMentors, setRecommendedMentors] = useState<RecommendedMentor[]>([]);

  // Optimization States
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [optimizationResult, setOptimizationResult] = useState<TrainingOptimizeResponse | null>(null);
  const [optimizationError, setOptimizationError] = useState<string | null>(null);

  // Active Batch Mentor Recommendation Expansion State
  const [selectedBatchIdForMentor, setSelectedBatchIdForMentor] = useState<string | null>(null);
  const [batchRecommendedMentors, setBatchRecommendedMentors] = useState<RecommendedMentor[]>([]);
  const [isLoadingBatchMentors, setIsLoadingBatchMentors] = useState(false);

  // Modal & Form States
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newType, setNewType] = useState<'webinar' | 'demo' | 'workshop' | 'seminar'>('webinar');
  const [newStartDate, setNewStartDate] = useState('');
  const [newEndDate, setNewEndDate] = useState('');
  const [newHours, setNewHours] = useState(2);
  const [newDesc, setNewDesc] = useState('');
  const [newLoc, setNewLoc] = useState('');
  const [newReg, setNewReg] = useState('');
  const [newInst, setNewInst] = useState('');
  const [newAud, setNewAud] = useState('');
  const [newMode, setNewMode] = useState<'online' | 'offline'>('online');
  const [newDom, setNewDom] = useState<'Data Science' | 'Data Analytics'>('Data Science');

  // AI Webinar Generator Modal & State
  const [isWebinarModalOpen, setIsWebinarModalOpen] = useState(false);
  const [isGeneratingWebinars, setIsGeneratingWebinars] = useState(false);
  const [downloadingPdfId, setDownloadingPdfId] = useState<string | number | null>(null);
  const [webinarDomain, setWebinarDomain] = useState('AI & Machine Learning');
  const [webinarFormat, setWebinarFormat] = useState('workshop');
  const [webinarAudience, setWebinarAudience] = useState('Software Engineers');
  const [webinarHours, setWebinarHours] = useState(2);
  const [webinarDesc, setWebinarDesc] = useState('');
  const [suggestedWebinars, setSuggestedWebinars] = useState<WebinarIdea[]>([]);

  const API_BASE = import.meta.env.VITE_BACKEND_URL || 'https://employee-allocation-ai.onrender.com';

  // Status Filter & Multi-Select States
  const [engagementStatusFilter, setEngagementStatusFilter] = useState<string>('all');
  const [selectedEngagementIds, setSelectedEngagementIds] = useState<string[]>([]);

  // 1. Fetch Real Engagements from API
  useEffect(() => {
    fetch(`${API_BASE}/api/training/engagements`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data: TrainingEngagement[]) => {
        setEngagements(data);
        if (data.length > 0) setSelectedEngagementId(data[0].engagement_id);
      })
      .catch((err) => {
        console.warn('API error fetching engagements, using fallback data:', err);
        setEngagements(fallbackEngagements);
        setSelectedEngagementId(fallbackEngagements[0].engagement_id);
      });
  }, []);

  // 2. Fetch Real Student Batches from API
  const fetchStudentBatches = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/training/student-batches`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: StudentBatch[] = await res.json();
      setBatches(data);
    } catch (e) {
      console.warn('API error fetching student batches, using fallback data:', e);
      setBatches(fallbackBatches);
    }
  };

  useEffect(() => {
    fetchStudentBatches();
  }, []);

  // 3. Fetch Real Recommended Mentors for Selected Engagement
  useEffect(() => {
    if (!selectedEngagementId) return;

    fetch(`${API_BASE}/api/training/engagements/${selectedEngagementId}/recommendations`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => setRecommendedMentors(data))
      .catch((err) => {
        console.warn('API error fetching engagement mentor recommendations, using fallback:', err);
        setRecommendedMentors(fallbackMentors);
      });
  }, [selectedEngagementId]);

  const selectedEngagement = 
    engagements.find((e) => e.engagement_id === selectedEngagementId) || engagements[0];

  // --- Filtering Logic ---
  const filteredEngagements = useMemo(() => {
    return engagements.filter((e) => {
      const matchesType = typeFilter === 'all' || e.engagement_type === typeFilter;
      const matchesStatus = engagementStatusFilter === 'all' || e.status === engagementStatusFilter;
      return matchesType && matchesStatus;
    });
  }, [engagements, typeFilter, engagementStatusFilter]);

  // --- Multi-Select & Selection Handlers ---
  const handleSelectEngagement = (engagementId: string) => {
    setSelectedEngagementIds((prev) =>
      prev.includes(engagementId)
        ? prev.filter((id) => id !== engagementId)
        : [...prev, engagementId]
    );
  };

  const handleToggleSelectAll = () => {
    const filterableIds = filteredEngagements.map((e) => e.engagement_id);
    const areAllSelected = filterableIds.length > 0 && filterableIds.every((id) => selectedEngagementIds.includes(id));

    if (areAllSelected) {
      setSelectedEngagementIds((prev) => prev.filter((id) => !filterableIds.includes(id)));
    } else {
      setSelectedEngagementIds((prev) => Array.from(new Set([...prev, ...filterableIds])));
    }
  };

  const clearSelection = () => {
    setSelectedEngagementIds([]);
  };

  // --- Global Training Speaker Optimization ---
  const handleOptimizeTrainings = async () => {
    const idsToOptimize =
      selectedEngagementIds.length > 0
        ? selectedEngagementIds
        : engagements.filter((e) => e.status === 'open' || e.status === 'proposed').map((e) => e.engagement_id);

    if (idsToOptimize.length === 0) {
      alert('Please select at least one engagement or ensure there are open/proposed engagements to optimize.');
      return;
    }

    setIsOptimizing(true);
    setOptimizationError(null);
    setSubTab('optimizations');

    try {
      const res = await fetch(`${API_BASE}/api/optimize/trainings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ engagement_ids: idsToOptimize }),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server returned status ${res.status}`);
      }

      const data: TrainingOptimizeResponse = await res.json();
      setOptimizationResult(data);
    } catch (err: any) {
      console.error('Training optimization failed:', err);
      setOptimizationError(err.message || 'Failed to complete global speaker optimization.');
    } finally {
      setIsOptimizing(false);
    }
  };

  // 4. Fetch Real Recommended Mentors for Student Batch Drawer
  const handleToggleBatchMentorDrawer = async (batch: StudentBatch) => {
    if (selectedBatchIdForMentor === batch.batch_id) {
      setSelectedBatchIdForMentor(null);
      return;
    }

    setSelectedBatchIdForMentor(batch.batch_id);
    setIsLoadingBatchMentors(true);

    try {
      const res = await fetch(`${API_BASE}/api/batches/${batch.batch_id}/recommended-mentors`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const formatted = data.map((item: any) => ({
        ...item,
        employee_id: item.employee_id || item.id,
        skills: item.skills || ['Domain Expert', 'Mentorship']
      }));
      setBatchRecommendedMentors(formatted);
    } catch (err) {
      console.warn('API error fetching batch mentor recommendations, using fallback:', err);
      setBatchRecommendedMentors(fallbackMentors);
    } finally {
      setIsLoadingBatchMentors(false);
    }
  };

  // Assign Mentor to Student Batch (PUT request to real API)
  const handleAssignBatchMentor = async (batchId: string, mentor: RecommendedMentor) => {
    const selectedMentorId = mentor.employee_id || mentor.id;
    if (!selectedMentorId) return;

    // Optimistic UI update
    setBatches((prev) =>
      prev.map((b) =>
        b.batch_id === batchId
          ? { ...b, trainer_ids: selectedMentorId, trainer_name: mentor.name }
          : b
      )
    );

    setSelectedBatchIdForMentor(null);

    try {
      const res = await fetch(`${API_BASE}/api/batches/${batchId}/assign-mentor`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mentor_id: selectedMentorId }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
    } catch (err) {
      console.error('API assignment failed, refreshing real batch data:', err);
      fetchStudentBatches();
    }
  };

  // Propose Mentor for Engagement
  const handleProposeMentor = async (engagementId: string, mentor: RecommendedMentor) => {
    setEngagements((prev) =>
      prev.map((e) =>
        e.engagement_id === engagementId
          ? { ...e, status: 'proposed', mentor_id: mentor.employee_id, mentor_name: mentor.name }
          : e
      )
    );

    try {
      const res = await fetch(`${API_BASE}/api/training/engagements/${engagementId}/propose`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mentor_id: mentor.employee_id }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
    } catch (err) {
      console.warn('API proposal request failed:', err);
    }
  };

  // Confirm Mentor Allocation for Engagement
  const handleConfirmAllocation = async (engagementId: string) => {
    setEngagements((prev) =>
      prev.map((e) => (e.engagement_id === engagementId ? { ...e, status: 'allocated' } : e))
    );

    try {
      const res = await fetch(`${API_BASE}/api/training/engagements/${engagementId}/confirm`, { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
    } catch (err) {
      console.warn('API confirmation request failed:', err);
    }
  };

  // Create New Engagement
  const handleScheduleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const generatedId = `rp2-train-${String(engagements.length + 1).padStart(4, '0')}`;
    const newEntry: TrainingEngagement = {
      engagement_id: generatedId,
      title: newTitle,
      engagement_type: newType,
      start_date: newStartDate || '2026-09-01',
      end_date: newEndDate || '2026-09-02',
      required_hours: newHours,
      status: 'open',
      description: newDesc,
      location: newLoc || 'Main Auditorium',
      region: newReg,
      audience: newAud,
      institution_name: newInst,
      mode: newMode,
      domain: newDom,
    };

    setEngagements([newEntry, ...engagements]);
    setIsModalOpen(false);
    setNewTitle('');
    setNewDesc('');

    try {
      const res = await fetch(`${API_BASE}/api/training/engagements`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newEntry)
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
    } catch (err) {
      console.warn('API engagement creation failed:', err);
    }
  };

  // Auto Generate Next Batch
  const handleAutoGenerateBatch = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/training/student-batches/auto-generate-next`, { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      
      const generated = await res.json();
      setBatches([...generated, ...batches]);
    } catch (e) {
      console.error('Failed to auto-generate batch:', e);
      alert('Failed to generate batch. Please try again or contact support.');
    }
  };

  const handleGenerateWebinarIdeas = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsGeneratingWebinars(true);

    try {
      const res = await fetch(`${API_BASE}/api/ai_events/suggest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          domain: webinarDomain,
          format_type: webinarFormat,
          target_audience: webinarAudience,
          duration_hours: webinarHours,
          description: webinarDesc,
        }),
      });

      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);

      const data = await res.json();
      const rawList = Array.isArray(data) ? data : (data.webinars || []);
      
      setSuggestedWebinars(rawList);
    } catch (err) {
      console.error('Failed to generate webinar ideas:', err);
    } finally {
      setIsGeneratingWebinars(false);
    }
  };

  // Download Webinar / Workshop Proposal PDF Handler
  const handleDownloadWebinarPdf = async (idea: WebinarIdea) => {
    const targetId = idea.id || idea.title;
    setDownloadingPdfId(targetId);

    try {
      const res = await fetch(`${API_BASE}/api/ai_events/generate-proposal-pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: idea.title,
          summary: idea.summary,
          format_type: idea.format_type,
          target_audience: idea.target_audience,
          duration_hours: idea.duration_hours,
        }),
      });

      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);

      const blob = await res.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      
      const safeTitle = (idea.title || 'Proposal').replace(/[^a-zA-Z0-9]/g, '_');
      link.download = `Syllabus_${safeTitle}.pdf`;
      
      document.body.appendChild(link);
      link.click();
      
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);
    } catch (err) {
      console.error('PDF download error:', err);
      alert('Failed to download proposal PDF.');
    } finally {
      setDownloadingPdfId(null);
    }
  };

  const renderStatusBadge = (status: EngagementStatus | string) => {
    switch (status) {
      case 'open':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-800 text-slate-400 border border-slate-700">
            <Clock className="w-3 h-3" /> open
          </span>
        );
      case 'proposed':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Send className="w-3 h-3" /> proposed
          </span>
        );
      case 'accepted':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <UserCheck className="w-3 h-3" /> accepted
          </span>
        );
      case 'rejected':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <XCircle className="w-3 h-3" /> rejected
          </span>
        );
      case 'allocated':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3 h-3" /> allocated
          </span>
        );
      case 'completed':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-purple-500/10 text-purple-400 border border-purple-500/20">
            <CheckCircle2 className="w-3 h-3" /> completed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-800 text-slate-300">
            {status}
          </span>
        );
    }
  };

  return (
  <div className="space-y-6">
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <h1 className="text-2xl font-bold text-white">Training & Knowledge Management</h1>
        <p className="text-slate-400 text-sm">Schedule webinars, workshops, demos, and auto-allocate student batches.</p>
      </div>
      <div className="flex items-center gap-3">
        {mainTab === 'engagements' ? (
          <>
          <button
            onClick={() => setIsModalOpen(true)}
            className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-2.5 rounded-xl flex items-center gap-2 shadow-lg transition-all"
          >
            <Plus className="w-4 h-4" /> Schedule Engagement
          </button>
          
            <button
              onClick={() => setIsWebinarModalOpen(true)}
              className="bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 text-xs font-semibold px-4 py-2.5 rounded-xl flex items-center gap-2 shadow-lg transition-all"
            >
              <Sparkles className="w-4 h-4 text-amber-400" /> Generate Idea
            </button>
          </>
        ) : null}
      </div>
    </div>

    <div className="flex border-b border-slate-800 gap-8">
      <button
        onClick={() => { setMainTab('engagements'); setSubTab('list'); }}
        className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-all ${
          mainTab === 'engagements'
            ? 'border-indigo-500 text-indigo-400'
            : 'border-transparent text-slate-400 hover:text-slate-200'
        }`}
      >
        <Video className="w-4 h-4" /> Training Engagements
      </button>
      <button
        onClick={() => setMainTab('student_batch')}
        className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-all ${
          mainTab === 'student_batch'
            ? 'border-indigo-500 text-indigo-400'
            : 'border-transparent text-slate-400 hover:text-slate-200'
        }`}
      >
        <GraduationCap className="w-4 h-4" /> Student Batches
      </button>
    </div>

    {mainTab === 'engagements' && (
      <div className="space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900 p-3 rounded-xl border border-slate-800">
          <div className="flex items-center gap-2 overflow-x-auto">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider px-2 flex items-center gap-1">
              <Filter className="w-3.5 h-3.5" /> Type:
            </span>
            {(['all', 'webinar', 'demo', 'workshop', 'seminar'] as EngagementTypeFilter[]).map((type) => (
              <button
                key={type}
                onClick={() => setTypeFilter(type)}
                className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-all capitalize ${
                  typeFilter === type
                    ? 'bg-indigo-600 text-white font-bold'
                    : 'bg-slate-950 text-slate-400 hover:text-slate-200 border border-slate-800'
                }`}
              >
                {type}
              </button>
            ))}
            {/* Engagement Status Filter */}
    <label className="text-xs text-slate-400 font-medium">STATUS:</label>
    <select
      value={engagementStatusFilter}
      onChange={(e) => setEngagementStatusFilter(e.target.value)}
      
      className="bg-slate-800 text-slate-200 border border-slate-700 rounded-md px-3 py-1.5 text-xs focus:outline-none focus:border-indigo-500"
      
    >
      
      <option value="all">All Statuses</option>
      <option value="open">Open</option>
      <option value="proposed">Proposed</option>
      <option value="accepted">Accepted</option>
      <option value="allocated">Allocated</option>
      <option value="rejected">Rejected</option>
      <option value="completed">Completed</option>
    </select>
          </div>

          <div className="flex items-center gap-2 border-t md:border-t-0 md:border-l border-slate-800 pt-2 md:pt-0 md:pl-4">
            <button
              onClick={() => setSubTab('list')}
              className={`text-xs px-3 py-1.5 rounded-lg font-medium ${
                subTab === 'list' ? 'bg-slate-800 text-indigo-400 font-bold' : 'text-slate-400 hover:text-white'
              }`}
            >
              List View
            </button>
            <button
              onClick={() => setSubTab('allocation')}
              className={`text-xs px-3 py-1.5 rounded-lg font-medium flex items-center gap-1 ${
                subTab === 'allocation' ? 'bg-slate-800 text-indigo-400 font-bold' : 'text-slate-400 hover:text-white'
              }`}
            >
              <Sliders className="w-3.5 h-3.5" /> Speaker Allocation
            </button>
          </div>
        </div>
        {/* Batch Selection Bar */}
<div className="flex items-center justify-between px-2 text-xs text-slate-400 mb-3">
  <label className="flex items-center gap-2 cursor-pointer select-none">
    <input
      type="checkbox"
      checked={
        filteredEngagements.length > 0 &&
        filteredEngagements.every((e) => selectedEngagementIds.includes(e.engagement_id))
      }
      onChange={handleToggleSelectAll}
      className="rounded bg-slate-900 border-slate-700 text-indigo-600 focus:ring-indigo-500 w-4 h-4"
    />
    <span>Select All ({selectedEngagementIds.length} selected)</span>
  </label>
  {selectedEngagementIds.length > 0 && (
    <button
      onClick={clearSelection}
      className="text-xs text-rose-400 hover:underline"
    >
      Clear Selection
    </button>
  )}
</div>
        {subTab === 'list' && (
  <Card
    title="Training Engagements"
    action={
      <button
        onClick={handleOptimizeTrainings}
        className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-semibold px-4 py-2.5 rounded-xl flex items-center gap-2 shadow-lg transition-all"
        type="button"
      >
        <FolderSync className="w-4 h-4" /> Optimize
      </button>
    }
  >
  <div className="space-y-3">
      {filteredEngagements.map((item) => {
        const isSelected = selectedEngagementIds?.includes(item.engagement_id);
        return (
          <div
            key={item.engagement_id}
            className={`p-4 bg-slate-950 border rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-4 transition-all hover:border-slate-700 ${
              isSelected ? 'border-indigo-500/60 bg-indigo-950/10' : 'border-slate-800'
            }`}
          >
            <div className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={isSelected}
                onChange={() => handleSelectEngagement(item.engagement_id)}
                className="mt-1 rounded bg-slate-900 border-slate-700 text-indigo-600 focus:ring-indigo-500 w-4 h-4 cursor-pointer"
              />
              <div className="p-2.5 bg-indigo-500/10 border border-indigo-500/20 rounded-lg text-indigo-400 mt-1">
                <Video className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h4 className="font-bold text-white text-base">{item.title}</h4>
                  <span className="text-[10px] uppercase bg-slate-900 border border-slate-700 px-2 py-0.5 rounded text-slate-300 font-semibold">
                    {item.engagement_type}
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-1">{item.description}</p>
                <p className="text-xs text-slate-400 mt-1">
                  Speaker: <span className="text-slate-200 font-medium">{item.mentor_name || 'Unassigned'}</span> • Location: <span className="text-slate-200 font-medium">{item.location || 'Unassigned'}</span> • Mode: <span className="text-slate-200 font-medium">{item.mode || 'Unassigned'}</span> • Duration: <span className="text-slate-300">{item.required_hours} hrs</span> • Schedule: <span className="text-slate-300">{item.start_date}</span>
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              {renderStatusBadge(item.status)}
              <button
                onClick={() => {
                  setSelectedEngagementId(item.engagement_id);
                  setSubTab('allocation');
                }}
                className="bg-slate-900 hover:bg-slate-800 text-slate-200 text-xs font-semibold px-3 py-2 rounded-lg border border-slate-700 flex items-center gap-1 transition-all"
              >
                Speaker Allocation <ArrowRight className="w-3.5 h-3.5 text-indigo-400" />
              </button>
            </div>
          </div>
        );
      })}
    </div>
  </Card>
)}

        {subTab === 'allocation' && (
          <Card title="Speaker Allocation Portal">
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 bg-slate-900 border border-slate-800 rounded-xl">
                <div>
                  <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                    Select Engagement
                  </label>
                  <select
                    value={selectedEngagementId}
                    onChange={(e) => setSelectedEngagementId(e.target.value)}
                    className="bg-slate-950 text-white text-sm font-semibold rounded-lg border border-slate-700 px-3 py-2 focus:outline-none focus:border-indigo-500 uppercase"
                  >
                    {engagements.map((w) => (
                      <option key={w.engagement_id} value={w.engagement_id}>
                        {w.title} ({w.engagement_type})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex items-center gap-3">
                  <span className="text-xs text-slate-400">Current Status:</span>
                  {renderStatusBadge(selectedEngagement.status)}
                </div>
              </div>

              {selectedEngagement.status === 'accepted' && (
                <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-xl flex items-center justify-between">
                  <div>
                    <p className="text-sm font-bold text-blue-300">Speaker Accepted Proposal!</p>
                    <p className="text-xs text-slate-400">{selectedEngagement.mentor_name} accepted the invitation to host.</p>
                  </div>
                  <button
                    onClick={() => handleConfirmAllocation(selectedEngagement.engagement_id)}
                    className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-all shadow-md"
                  >
                    Confirm Allocation
                  </button>
                </div>
              )}

              <div className="space-y-4 pt-2">
                <h4 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-indigo-400" /> AI Skill-Matched Mentors
                </h4>

                <div className="grid grid-cols-1 gap-3">
                  {recommendedMentors.map((mentor) => {
                    const isProposed = selectedEngagement.mentor_id === mentor.employee_id;

                    return (
                      <div
                        key={mentor.employee_id}
                        className={`p-4 bg-slate-950 border rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-4 transition-all ${
                          isProposed ? 'border-indigo-500/50 bg-indigo-950/10' : 'border-slate-800'
                        }`}
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <h5 className="font-bold text-white text-base">{mentor.name}</h5>
                            <span className="text-xs bg-emerald-500/10 text-emerald-400 font-mono px-2 py-0.5 rounded border border-emerald-500/20 flex items-center gap-1">
                              <Star className="w-3 h-3 fill-emerald-400" /> {mentor.match_score}% Match
                            </span>
                          </div>
                          <p className="text-xs text-slate-400">{mentor.designation} • ID: {mentor.employee_id}</p>

                          <div className="flex flex-wrap gap-1 pt-1">
                            {(mentor.skills ?? []).map((skill, i) => (
                              <span key={i} className="text-[10px] bg-slate-900 text-slate-400 px-2 py-0.5 rounded border border-slate-800">
                                {skill}
                              </span>
                            ))}
                          </div>
                        </div>

                        <div>
                          {selectedEngagement.status === 'open' || selectedEngagement.status === 'rejected' ? (
                            <button
                              onClick={() => handleProposeMentor(selectedEngagement.engagement_id, mentor)}
                              className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-2 rounded-lg flex items-center gap-1.5 transition-all shadow-md"
                            >
                              <UserPlus className="w-3.5 h-3.5" /> Propose Speaker
                            </button>
                          ) : null}

                          {isProposed && selectedEngagement.status === 'proposed' && (
                            <span className="text-xs text-amber-400 font-medium italic flex items-center gap-1.5 bg-amber-500/10 px-3 py-1.5 rounded-lg border border-amber-500/20">
                              <Clock className="w-3.5 h-3.5" /> Proposed (Awaiting Response)
                            </span>
                          )}

                          {isProposed && selectedEngagement.status === 'allocated' && (
                            <span className="text-xs text-emerald-400 font-bold flex items-center gap-1.5 bg-emerald-500/10 px-3 py-1.5 rounded-lg border border-emerald-500/20">
                              <CheckCircle2 className="w-3.5 h-3.5" /> Allocated Speaker
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </Card>
        )}
      </div>
    )}
    {/* Subtab: Optimizations View */}
{subTab === 'optimizations' && (
  <div className="space-y-6">
    {/* Header & Control Bar */}
    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-slate-900/60 p-5 rounded-xl border border-slate-800">
      <div>
        <h3 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-amber-400" /> Global Speaker Optimization Results
        </h3>
        <p className="text-sm text-slate-400 mt-0.5">
          AI-driven candidate matching based on engagement requirements, domain expertise, and availability.
        </p>
      </div>

      <button
        onClick={handleOptimizeTrainings}
        disabled={isOptimizing}
        className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 text-white text-sm font-medium rounded-lg transition-colors shadow-lg shadow-indigo-600/20 shrink-0"
      >
        {isOptimizing ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin text-white" />
            Optimizing...
          </>
        ) : (
          <>
            <RefreshCw className="w-4 h-4" />
            Re-run Optimization
          </>
        )}
      </button>
    </div>

    {/* Loading State */}
    {isOptimizing && (
      <Card className="p-12 text-center bg-slate-900/40 border-slate-800">
        <div className="flex flex-col items-center justify-center space-y-4">
          <div className="p-4 rounded-full bg-indigo-500/10 text-indigo-400 animate-pulse">
            <Sparkles className="w-8 h-8 animate-spin" />
          </div>
          <div>
            <h4 className="text-base font-semibold text-slate-200">Analyzing Trainer Matches</h4>
            <p className="text-sm text-slate-400 max-w-md mx-auto mt-1">
              Evaluating candidate skills, required engagement hours, and availability metrics...
            </p>
          </div>
        </div>
      </Card>
    )}

    {/* Error State */}
    {!isOptimizing && optimizationError && (
      <Card className="p-6 bg-rose-950/20 border-rose-800/40">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div>
            <h4 className="text-sm font-semibold text-rose-300">Optimization Failed</h4>
            <p className="text-sm text-rose-400/80 mt-1">{optimizationError}</p>
          </div>
        </div>
      </Card>
    )}

    {/* Empty State */}
    {!isOptimizing && !optimizationResult && !optimizationError && (
      <Card className="p-12 text-center bg-slate-900/40 border-slate-800">
        <Sliders className="w-10 h-10 text-slate-600 mx-auto mb-3" />
        <h4 className="text-base font-semibold text-slate-300">No Optimization Results Available</h4>
        <p className="text-sm text-slate-500 max-w-sm mx-auto mt-1 mb-4">
          Run global optimization to generate recommended speaker allocations based on current demand.
        </p>
        <button
          onClick={handleOptimizeTrainings}
          className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors"
        >
          <Sparkles className="w-4 h-4" /> Run Speaker Optimization
        </button>
      </Card>
    )}

    {/* Results View */}
    {!isOptimizing && optimizationResult && (
      <div className="space-y-6">
        {/* Metric Overview Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Optimized Assignments</span>
            <div className="text-2xl font-bold text-white mt-1 flex items-center gap-2">
              {optimizationResult.assignments.length}
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Unstaffed Engagements</span>
            <div className="text-2xl font-bold text-amber-400 mt-1 flex items-center gap-2">
              {optimizationResult.unstaffed_engagements?.length || 0}
              {(optimizationResult.unstaffed_engagements?.length || 0) > 0 && (
                <Clock className="w-5 h-5 text-amber-400" />
              )}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Average Match Score</span>
            <div className="text-2xl font-bold text-indigo-400 mt-1 flex items-center gap-1">
              {(
                (optimizationResult.assignments.reduce((acc, curr) => acc + curr.score, 0) /
                  (optimizationResult.assignments.length || 1))
              ).toFixed(1)}%
              <Star className="w-5 h-5 text-indigo-400 fill-indigo-400/20" />
            </div>
          </div>
        </div>

        {/* Assignments Matrix Grid */}
        <div className="space-y-4">
          <h3 className="text-base font-semibold text-white flex items-center gap-2">
            <Crown className="w-4 h-4 text-amber-400" /> Optimal Speaker Allocations
          </h3>

          <div className="grid grid-cols-1 gap-4">
            {optimizationResult.assignments.map((assignment) => {
              const engagement = engagements.find((e) => e.engagement_id === assignment.engagement_id);
              const scorePct = (assignment.score).toFixed(1);

              const currentStatus = engagement?.status || 'open';
              const isProposed = currentStatus === 'proposed';
              const isAccepted = currentStatus === 'accepted';
              const isRejected = currentStatus === 'rejected';
              const isAllocated = currentStatus === 'allocated';

              return (
                <div
                  key={assignment.engagement_id}
                  className="bg-slate-900/70 border border-slate-800 hover:border-slate-700/80 rounded-xl p-5 transition-all space-y-4"
                >
                  {/* Top Bar: Engagement Info & Match Score */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                          {assignment.engagement_id}
                        </span>
                        <h4 className="text-base font-semibold text-white">
                          {engagement ? engagement.title : `Engagement ${assignment.engagement_id}`}
                        </h4>
                        {renderStatusBadge(currentStatus)}
                      </div>
                      <div className="flex items-center gap-4 text-xs text-slate-400 mt-1">
                        <span>{engagement?.required_hours || 0} Hours Required</span>
                        <span>•</span>
                        <span>{engagement?.engagement_type || 'Training'}</span>
                        {engagement?.location && (
                          <>
                            <span>•</span>
                            <span>{engagement.location}</span>
                          </>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-medium">
                        <Star className="w-3.5 h-3.5 fill-indigo-400" />
                        <span>{scorePct}% Compatibility</span>
                      </div>
                    </div>
                  </div>

                  {/* Allocation Details: Recommended Candidate & Action */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Suggested Speaker Details */}
                    <div className="bg-slate-800/40 rounded-lg p-4 border border-slate-800/80 flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wide flex items-center gap-1">
                            <Users className="w-3.5 h-3.5" /> Optimal Lead Speaker
                          </span>
                        </div>

                        <div className="font-medium text-white text-sm">{assignment.candidate_name}</div>
                        <div className="text-xs text-slate-400 font-mono mt-0.5">ID: {assignment.candidate_id}</div>

                        {/* Candidate Skills */}
                        {assignment.candidate_skills && assignment.candidate_skills.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 mt-3">
                            {assignment.candidate_skills.map((skill, idx) => (
                              <span
                                key={idx}
                                className="text-[11px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700"
                              >
                                {skill}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Action & Status Workflow Control Box */}
                    <div className="bg-slate-800/40 rounded-lg p-4 border border-slate-800/80 flex flex-col justify-center items-center text-center">
                      {/* State 1: Open -> Propose Speaker */}
                      {currentStatus === 'open' && (
                        <div className="w-full space-y-2">
                          <p className="text-xs text-slate-400">Ready to send candidate proposal</p>
                          <button
                            onClick={() =>
                              handleProposeMentor(assignment.engagement_id, {
                                employee_id: assignment.candidate_id,
                                name: assignment.candidate_name,
                                designation: 'AI Recommended Speaker',
                                match_score: assignment.score,
                                skills: assignment.candidate_skills,
                              })
                            }
                            className="w-full py-2.5 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition-colors flex items-center justify-center gap-2 shadow-md shadow-indigo-600/20"
                          >
                            <Send className="w-3.5 h-3.5" /> Propose Speaker
                          </button>
                        </div>
                      )}

                      {/* State 2: Proposed -> Awaiting Employee Response */}
                      {isProposed && (
                        <div className="w-full p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-medium flex items-center justify-center gap-2">
                          <Hourglass className="w-4 h-4 animate-spin shrink-0" />
                          <span>Proposal Sent (Awaiting Employee Response)</span>
                        </div>
                      )}

                      {/* State 3: Accepted by Employee -> Show Confirm Button */}
                      {isAccepted && (
                        <div className="w-full space-y-2">
                          <p className="text-xs text-emerald-400 font-medium flex items-center justify-center gap-1">
                            <CheckCircle2 className="w-3.5 h-3.5" /> Employee Accepted Proposal
                          </p>
                          <button
                            onClick={() => handleConfirmAllocation(assignment.engagement_id)}
                            className="w-full py-2.5 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition-colors flex items-center justify-center gap-2 shadow-md shadow-emerald-600/20"
                          >
                            <CheckCircle2 className="w-3.5 h-3.5" /> Confirm Final Allocation
                          </button>
                        </div>
                      )}

                      {/* State 4: Rejected -> Substitute Required */}
                      {isRejected && (
                        <div className="w-full space-y-2">
                          <p className="text-xs text-rose-400 font-medium flex items-center justify-center gap-1">
                            <XCircle className="w-3.5 h-3.5" /> Employee Declined Proposal
                          </p>
                          <button
                            onClick={() => {
                              setSelectedEngagementId(assignment.engagement_id);
                              setSubTab('allocation');
                            }}
                            className="w-full py-2 px-3 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium rounded-lg transition-colors flex items-center justify-center gap-1.5"
                          >
                            <UserPlus className="w-3.5 h-3.5 text-indigo-400" /> Find Substitute
                          </button>
                        </div>
                      )}

                      {/* State 5: Fully Allocated */}
                      {isAllocated && (
                        <div className="w-full p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold flex items-center justify-center gap-2">
                          <CheckCircle2 className="w-4 h-4" />
                          <span>Speaker Fully Allocated</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Unstaffed Engagements Warning Box */}
        {optimizationResult.unstaffed_engagements &&
          optimizationResult.unstaffed_engagements.length > 0 && (
            <div className="p-5 rounded-xl bg-amber-500/10 border border-amber-500/20 space-y-3">
              <div className="flex items-center gap-2 text-amber-400 font-medium text-sm">
                <XCircle className="w-4 h-4" /> Unstaffed Engagements ({optimizationResult.unstaffed_engagements.length})
              </div>
              <p className="text-xs text-slate-400">
                The constraint solver could not fulfill resource requirements for the following engagements without breaking allocation parameters:
              </p>
              <div className="flex flex-wrap gap-2 pt-1">
                {optimizationResult.unstaffed_engagements.map((engId) => (
                  <button
                    key={engId}
                    onClick={() => {
                      setSelectedEngagementId(engId);
                      setSubTab('allocation');
                    }}
                    className="px-2.5 py-1 rounded bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 text-xs font-mono border border-amber-500/30 transition-colors flex items-center gap-1"
                  >
                    <span>{engId}</span>
                    <ArrowRight className="w-3 h-3 opacity-60" />
                  </button>
                ))}
              </div>
            </div>
          )}
      </div>
    )}
  </div>
)}
    {/* STUDENT BATCH TAB CONTENT */}
      {mainTab === 'student_batch' && (
        <div className="space-y-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900 p-3 rounded-xl border border-slate-800">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-indigo-400 shrink-0" />
              <div className="text-xs text-slate-300 leading-relaxed">
                <span className="font-bold text-indigo-300">Batch Mentor Management:</span> Click <span className="text-indigo-400 font-semibold">Change Mentor</span> on any batch to view AI recommendations and update assignments.
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={handleAutoGenerateBatch}
                className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-all shadow-sm"
              >
                <Plus className="w-4 h-4" /> Auto-Generate Batch
              </button>
            </div>
          </div>

          <Card title="Student Batches">
            <div className="space-y-3">
              {batches.length === 0 ? (
                <div className="p-8 text-center text-xs text-slate-400 bg-slate-950 border border-slate-800 rounded-xl">
                  No student batches found.
                </div>
              ) : (
                batches.map((batch) => {
                  const isSelecting = selectedBatchIdForMentor === batch.batch_id;

                  return (
                    <div
                      key={batch.batch_id}
                      className={`p-4 bg-slate-950 border rounded-xl transition-all ${
                        isSelecting ? 'border-indigo-500/70 bg-indigo-950/10' : 'border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div className="flex items-center gap-3">
                          <div className="p-2.5 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-emerald-400">
                            <GraduationCap className="w-5 h-5" />
                          </div>
                          <div>
                            <div className="flex items-center gap-2 flex-wrap">
                              <h4 className="font-bold text-white text-sm">{batch.batch_name}</h4>
                              {batch.domain && (
                                <span className="text-[10px] bg-slate-900 text-slate-300 px-2 py-0.5 rounded border border-slate-700">
                                  {batch.domain}
                                </span>
                              )}
                              {batch.status && (
                                <span
                                  className={`text-[10px] px-2 py-0.5 rounded border capitalize ${
                                    batch.status === 'open' || batch.status === 'active'
                                      ? 'bg-emerald-950/40 text-emerald-400 border-emerald-500/30'
                                      : 'bg-slate-900 text-slate-400 border-slate-700'
                                  }`}
                                >
                                  {batch.status}
                                </span>
                              )}
                            </div>
                            <p className="text-xs text-slate-400 mt-1">
                              Duration: <span className="text-slate-200">{batch.start_date || 'N/A'}</span> to <span className="text-slate-200">{batch.end_date || 'N/A'}</span> • Mode: <span className="text-slate-300 capitalize">{batch.delivery_mode || 'online'}</span>
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center gap-3">
                          {/* Current Assigned Mentor Badge */}
                          <div className="flex flex-col items-start md:items-end bg-slate-900 border border-slate-800 px-3.5 py-2 rounded-lg shrink-0">
                            <span className="text-[10px] uppercase tracking-wider text-slate-400 font-medium">Assigned Mentor</span>
                            <span className="text-xs font-bold text-indigo-400 mt-0.5">
                              {batch.trainer_name || 'Unassigned'}
                            </span>
                          </div>

                          {/* Action Button: Triggers Mentor Selection Drawer */}
                          <button
                            onClick={() => handleToggleBatchMentorDrawer(batch)}
                            className={`text-xs font-semibold px-3 py-2 rounded-lg border flex items-center gap-1.5 transition-all shrink-0 ${
                              isSelecting
                                ? 'bg-indigo-600 text-white border-indigo-500 shadow-lg'
                                : 'bg-slate-900 hover:bg-slate-800 text-slate-200 border-slate-700'
                            }`}
                          >
                            <UserPlus className="w-3.5 h-3.5 text-indigo-400" />
                            {isSelecting ? 'Cancel' : 'Change Mentor'}
                          </button>
                        </div>
                      </div>

                      {/* INLINE RECOMMENDED MENTORS EXPANSION PANEL */}
                      {isSelecting && (
                        <div className="mt-4 pt-4 border-t border-slate-800/80 space-y-3 bg-slate-900/60 -mx-4 -mb-4 p-4 rounded-b-xl">
                          <div className="flex items-center justify-between">
                            <h5 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                              <Sparkles className="w-4 h-4 text-amber-400" /> Recommended Mentors for {batch.batch_name}
                            </h5>
                            <span className="text-[11px] text-slate-400">Click assign to set as new mentor</span>
                          </div>

                          {isLoadingBatchMentors ? (
                            <div className="p-4 text-center text-xs text-slate-400">Loading AI recommendations...</div>
                          ) : (
                            <div className="grid grid-cols-1 gap-2.5">
                              {batchRecommendedMentors.map((mentor) => {
                                const mentorId = mentor.employee_id || mentor.id;
                                const isCurrentlyAssigned = batch.trainer_name === mentor.name || batch.trainer_ids === mentorId;

                                return (
                                  <div
                                    key={mentorId}
                                    className={`p-3 bg-slate-950 border rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-3 transition-all ${
                                      isCurrentlyAssigned
                                        ? 'border-emerald-500/50 bg-emerald-950/10'
                                        : 'border-slate-800 hover:border-slate-700'
                                    }`}
                                  >
                                    <div className="space-y-1">
                                      <div className="flex items-center gap-2">
                                        <h6 className="font-bold text-white text-sm">{mentor.name}</h6>
                                        <span className="text-[10px] bg-emerald-500/10 text-emerald-400 font-mono px-2 py-0.5 rounded border border-emerald-500/20 flex items-center gap-1">
                                          <Star className="w-3 h-3 fill-emerald-400" /> {mentor.match_score}% Fit
                                        </span>
                                        {isCurrentlyAssigned && (
                                          <span className="text-[10px] bg-emerald-500/20 text-emerald-300 font-semibold px-2 py-0.5 rounded border border-emerald-500/40">
                                            Currently Assigned
                                          </span>
                                        )}
                                      </div>
                                      <p className="text-[11px] text-slate-400">
                                        {mentor.designation} • ID: {mentorId}
                                      </p>
                                      <div className="flex flex-wrap gap-1 pt-0.5">
                                        {(mentor.skills ?? []).map((skill, i) => (
                                          <span
                                            key={i}
                                            className="text-[9px] bg-slate-900 text-slate-400 px-1.5 py-0.5 rounded border border-slate-800"
                                          >
                                            {skill}
                                          </span>
                                        ))}
                                      </div>
                                    </div>

                                    <div>
                                      {!isCurrentlyAssigned ? (
                                        <button
                                          onClick={() => handleAssignBatchMentor(batch.batch_id, mentor)}
                                          className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all shadow-md shrink-0"
                                        >
                                          <CheckCircle2 className="w-3.5 h-3.5" /> Assign to Batch
                                        </button>
                                      ) : (
                                        <span className="text-xs text-emerald-400 font-semibold flex items-center gap-1 bg-emerald-500/10 px-3 py-1.5 rounded-lg border border-emerald-500/20">
                                          <CheckCircle2 className="w-3.5 h-3.5" /> Active
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </Card>
        </div>
      )}

      {/* Ensure array check handles both direct arrays and potential state objects */}
{Array.isArray(suggestedWebinars) && suggestedWebinars.length > 0 && (
  <div className="pt-6 border-t border-slate-800 space-y-4">
    <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
      <Sparkles className="w-4 h-4 text-amber-400" /> 
      Generated Workshop Ideas ({suggestedWebinars.length})
    </h3>

    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {suggestedWebinars.map((idea) => (
        <Card key={idea.id} className="p-5 bg-slate-900 border-slate-800 flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-start justify-between gap-2">
              <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                {idea.format_type}
              </span>
              <span className="text-xs text-slate-400">
                {idea.duration_hours} hrs
              </span>
            </div>

            <h4 className="font-bold text-white text-base leading-snug">{idea.title}</h4>
            <p className="text-xs text-slate-400 leading-relaxed">{idea.summary}</p>
          </div>

          <div className="pt-4 mt-4 border-t border-slate-800">
            <button
              onClick={() => handleDownloadWebinarPdf(idea)}
              disabled={downloadingPdfId === idea.id}
              className="w-full bg-slate-950 hover:bg-slate-800 text-slate-200 text-xs font-semibold py-2 rounded-lg border border-slate-700"
            >
              {downloadingPdfId === idea.id ? 'Generating PDF...' : 'Download Proposal PDF'}
            </button>
          </div>
        </Card>
      ))}
    </div>
  </div>
)}



    {isModalOpen && (
      <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 space-y-4 shadow-2xl">
          <h3 className="text-lg font-bold text-white">Schedule New Engagement</h3>

          <form onSubmit={handleScheduleSubmit} className="space-y-4">
            <div>
              <label className="text-xs text-slate-400 block mb-1">Title</label>
              <input
                type="text"
                required
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                placeholder="e.g. Distributed Consensus in Go"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Engagement Type</label>
                <select
                  value={newType}
                  onChange={(e) => setNewType(e.target.value as any)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="webinar">webinar</option>
                  <option value="demo">demo</option>
                  <option value="workshop">workshop</option>
                  <option value="seminar">seminar</option>
                </select>
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">Required Hours</label>
                <input
                  type="number"
                  min={1}
                  value={newHours}
                  onChange={(e) => setNewHours(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Start Date</label>
                <input
                  type="date"
                  required
                  value={newStartDate}
                  onChange={(e) => setNewStartDate(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">End Date</label>
                <input
                  type="date"
                  value={newEndDate}
                  onChange={(e) => setNewEndDate(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Domain</label>
                <select
                  value={newDom}
                  onChange={(e) => setNewDom(e.target.value as any)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="Data Science">Data Science</option>
                  <option value="Data Analytics">Data Analytics</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Location</label>
                <input
                  type="string"
                  value={newLoc}
                  onChange={(e) => setNewLoc(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                  placeholder="Kochi"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Region</label>
                <input
                  type="string"
                  value={newReg}
                  onChange={(e) => setNewReg(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                  placeholder="Kochi"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Institution</label>
                <input
                  type="string"
                  value={newInst}
                  onChange={(e) => setNewInst(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                  placeholder="eg: CUSAT"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Mode</label>
                <select
                  value={newMode}
                  onChange={(e) => setNewMode(e.target.value as any)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="online">online</option>
                  <option value="offline">offline</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Audience</label>
                <input
                  type="string"
                  value={newAud}
                  onChange={(e) => setNewAud(e.target.value as any)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                  placeholder="college_students"
                />
              </div>
            </div>

            <div>
              <label className="text-xs text-slate-400 block mb-1">Description</label>
              <textarea
                rows={3}
                value={newDesc}
                onChange={(e) => setNewDesc(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                placeholder="Details for pgvector skill extraction..."
              />
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-2 rounded-lg"
              >
                Schedule Engagement
              </button>
            </div>
          </form>
        </div>
      </div>)}
      
      {/* AI WEBINAR REQUIREMENT FORM MODAL */}
      {isWebinarModalOpen && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 space-y-4 shadow-2xl relative">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-amber-400" /> AI Workshop Idea Generator
              </h3>
              <button onClick={() => setIsWebinarModalOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleGenerateWebinarIdeas} className="space-y-4">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Domain / Subject</label>
                <input
                  type="text"
                  required
                  value={webinarDomain}
                  onChange={(e) => setWebinarDomain(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                  placeholder="e.g. AI & Machine Learning, DevOps"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Format Type</label>
                  <select
                    value={webinarFormat}
                    onChange={(e) => setWebinarFormat(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-indigo-500 capitalize"
                  >
                    <option value="workshop">Workshop</option>
                    <option value="webinar">Webinar</option>
                    <option value="demo">Demo</option>
                    <option value="seminar">Seminar</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs text-slate-400 block mb-1">Duration (Hours)</label>
                  <input
                    type="number"
                    min={1}
                    max={40}
                    value={webinarHours}
                    onChange={(e) => setWebinarHours(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">Target Audience</label>
                <input
                  type="text"
                  required
                  value={webinarAudience}
                  onChange={(e) => setWebinarAudience(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                  placeholder="e.g. Software Engineers, Students"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">Additional Notes (Optional)</label>
                <textarea
                  rows={3}
                  value={webinarDesc}
                  onChange={(e) => setWebinarDesc(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                  placeholder="Specify focus areas..."
                />
              </div>

              <div className="flex justify-end gap-3 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsWebinarModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isGeneratingWebinars}
                  className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-2.5 rounded-lg flex items-center gap-2 transition-all disabled:opacity-50"
                >
                  {isGeneratingWebinars ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" /> Generating...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4 text-amber-400" /> Fetch Ideas
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
    )}
  </div>
)};