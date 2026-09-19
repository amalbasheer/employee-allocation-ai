import React, { useState, useEffect, useMemo } from 'react';
import { Card } from '../../components/common/Card';
import { 
  Video, Plus, Clock, CheckCircle2, XCircle, Send, Pencil, Edit2, Trash2,
  UserCheck, Star, UserPlus, Sliders, ArrowRight, Download, Database, BarChart3,
  GraduationCap, RefreshCw, Sparkles, Filter, AlertCircle, Layers, Bot, 
} from 'lucide-react';

export interface RecommendedMentor {
  employee_id: string;
  id?: string;
  name: string;
  designation: string;
  match_score: number;
  skills?: string[];
  is_team_lead?: boolean;
  batch_count?: number;
  session?: string;
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
  session?: string;
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
export const StudentBatches: React.FC = () => {
  const [mainTab, setMainTab] = useState<'student_batch'>('student_batch');
  const [subTab, setSubTab] = useState<'list' | 'allocation' | 'optimizations'>('list');

  // Domain Filter Tab State ('all' | 'DS' | 'DA' | 'Agentic AI')
  const [activeDomainTab, setActiveDomainTab] = useState<string>('all');

  // Real Data States
  const [batches, setBatches] = useState<StudentBatch[]>([]);
  const [selectedEngagementId, setSelectedEngagementId] = useState<string>('');
  const [recommendedMentors, setRecommendedMentors] = useState<RecommendedMentor[]>([]);

  // Optimization States
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [optimizationError, setOptimizationError] = useState<string | null>(null);

  // Active Batch Mentor Recommendation Expansion State
  const [selectedBatchIdForMentor, setSelectedBatchIdForMentor] = useState<string | null>(null);
  const [batchRecommendedMentors, setBatchRecommendedMentors] = useState<RecommendedMentor[]>([]);
  const [isLoadingBatchMentors, setIsLoadingBatchMentors] = useState(false);

  // Modal & Form States
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);

  const API_BASE = import.meta.env.VITE_BACKEND_URL || 'https://employee-allocation-ai.onrender.com';

  // Fetch Real Student Batches from API
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

  // Fetch Real Recommended Mentors for Student Batch Drawer
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
        skills: item.skills || ['Domain Expert', 'Mentorship'],
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

  // Auto Generate Next Batch
  const handleAutoGenerateBatch = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/training/student-batches/auto-generate-next`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const generated = await res.json();
      setBatches([...generated, ...batches]);
    } catch (e) {
      console.error('Failed to auto-generate batch:', e);
      alert('Failed to generate batch. Please try again or contact support.');
    }
  };

  // Domain Helper Matching (Handles casing and shorthand variations)
const matchDomain = (batchDomain: string | undefined, targetKey: string): boolean => {
  if (!batchDomain) return false;
  const dom = batchDomain.toLowerCase().trim();

  if (targetKey === 'DS') {
    return dom === 'ds' || dom.includes('data science');
  }
  if (targetKey === 'DA') {
    return dom === 'da' || dom.includes('data analytics') || dom.includes('analytics');
  }
  if (targetKey === 'Agentic AI') {
    return dom.includes('agentic') || dom === 'ai' || dom.includes('agentic ai');
  }
  return false;
};

// Main tab-filtered list for rendering in the active tab view
const filteredBatches = useMemo(() => {
  if (activeDomainTab === 'all') return batches;
  return batches.filter((batch) => matchDomain(batch.domain, activeDomainTab));
}, [batches, activeDomainTab]);

// Dedicated domain lists using the same helper function
const dsBatches = useMemo(
  () => batches.filter((b) => matchDomain(b.domain, 'DS')),
  [batches]
);

const daBatches = useMemo(
  () => batches.filter((b) => matchDomain(b.domain, 'DA')),
  [batches]
);

const agenticAiBatches = useMemo(
  () => batches.filter((b) => matchDomain(b.domain, 'Agentic AI')),
  [batches]
);

// Tab counter badge helper
const getDomainCount = (domainKey: string) => {
  if (domainKey === 'all') return batches.length;
  return batches.filter((b) => matchDomain(b.domain, domainKey)).length;
};

  const domainTabs = [
    { id: 'all', label: 'All Batches', icon: Layers },
    { id: 'DS', label: 'Data Science (DS)', icon: Database },
    { id: 'DA', label: 'Data Analytics (DA)', icon: BarChart3 },
    { id: 'Agentic AI', label: 'Agentic AI', icon: Bot },
  ];
return (
  <div className="space-y-6">
    {/* Page Header Section */}
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800/60">
      <div>
        <h1 className="text-2xl font-bold text-white">Student Batch Management</h1>
        <p className="text-slate-400 text-sm mt-1">
          Schedule and auto-allocate student batches for DS, DA, Agentic AI.
        </p>
      </div>
    </div>

    {/* Domain Tabs (DS, DA, Agentic AI) */}
    <div className="flex items-center gap-2 border-b border-slate-800 text-sm font-medium">
      {[
        { id: 'all', label: 'All Domains' },
        { id: 'DS', label: 'Data Science (DS)' },
        { id: 'DA', label: 'Data Analytics (DA)' },
        { id: 'Agentic AI', label: 'Agentic AI' },
      ].map((tab) => {
        const count =
          tab.id === 'all'
            ? batches.length
            : batches.filter((b) => matchDomain(b.domain, tab.id)).length;

        const isActive = activeDomainTab === tab.id;

        return (
          <button
            key={tab.id}
            onClick={() => setActiveDomainTab(tab.id)}
            className={`pb-3 px-3 flex items-center gap-2 transition-all border-b-2 text-xs font-semibold ${
              isActive
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            {tab.label}
            <span
              className={`px-2 py-0.5 text-[10px] rounded-full border ${
                isActive
                  ? 'bg-indigo-950/60 text-indigo-300 border-indigo-500/40'
                  : 'bg-slate-900 text-slate-400 border-slate-800'
              }`}
            >
              {count}
            </span>
          </button>
        );
      })}
    </div>

    {/* Main Content Area */}
    <div className="space-y-6">
      {/* Banner Action Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900 p-3 rounded-xl border border-slate-800">
        <div className="flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-indigo-400 shrink-0" />
          <div className="text-xs text-slate-300 leading-relaxed">
            <span className="font-bold text-indigo-300">Batch Mentor Management:</span> Click{' '}
            <span className="text-indigo-400 font-semibold">Change Mentor</span> on any batch to view AI recommendations and update assignments.
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

      {/* Batches Card List */}
      <Card
        title={
          activeDomainTab === 'all'
            ? 'All Student Batches'
            : `${activeDomainTab} Batches`
        }
      >
        <div className="space-y-3">
          {batches.filter(
            (b) => activeDomainTab === 'all' || matchDomain(b.domain, activeDomainTab)
          ).length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-400 bg-slate-950 border border-slate-800 rounded-xl">
              No batches found for {activeDomainTab === 'all' ? 'any domain' : activeDomainTab}.
            </div>
          ) : (
            batches
              .filter(
                (b) => activeDomainTab === 'all' || matchDomain(b.domain, activeDomainTab)
              )
              .map((batch) => {
                const isSelecting = selectedBatchIdForMentor === batch.batch_id;

                return (
                  <div
                    key={batch.batch_id}
                    className={`p-4 bg-slate-950 border rounded-xl transition-all ${
                      isSelecting
                        ? 'border-indigo-500/70 bg-indigo-950/10'
                        : 'border-slate-800 hover:border-slate-700'
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
                              <span className="text-[10px] bg-slate-900 text-indigo-300 font-semibold px-2 py-0.5 rounded border border-indigo-500/30">
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
                            Duration: <span className="text-slate-200">{batch.start_date || 'N/A'}</span> to{' '}
                            <span className="text-slate-200">{batch.end_date || 'N/A'}</span> • Mode:{' '}
                            <span className="text-slate-300 capitalize">{batch.delivery_mode || 'online'}</span> • Session:{' '}
                            <span className="text-slate-300 capitalize">{batch.session || 'morning'}</span>
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-3">
                        {/* Current Assigned Mentor Badge */}
                        <div className="flex flex-col items-start md:items-end bg-slate-900 border border-slate-800 px-3.5 py-2 rounded-lg shrink-0">
                          <span className="text-[10px] uppercase tracking-wider text-slate-400 font-medium">
                            Assigned Mentor
                          </span>
                          <span className="text-xs font-bold text-indigo-400 mt-0.5">
                            {batch.trainer_name || 'Unassigned'}
                          </span>
                        </div>

                        {/* Action Button */}
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

                    {/* Inline Recommended Mentors Expansion Panel */}
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
                              const isCurrentlyAssigned =
                                batch.trainer_name === mentor.name || batch.trainer_ids === mentorId;

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
  </div>
);}