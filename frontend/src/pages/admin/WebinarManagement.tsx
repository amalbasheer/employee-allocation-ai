import React, { useState, useEffect } from 'react';
import { Card } from '../../components/common/Card';
import { 
  Video, Plus, Clock, CheckCircle2, XCircle, Send, 
  UserCheck, Star, UserPlus, Sliders, ArrowRight,
  GraduationCap, RefreshCw, Sparkles, Filter, AlertCircle
} from 'lucide-react';

export type EngagementTypeFilter = 'all' | 'webinar' | 'demo' | 'workshop' | 'seminar';

// Standard lowercase string statuses matching DB definitions
export type EngagementStatus = 'open' | 'proposed' | 'accepted' | 'rejected' | 'allocated' | 'completed';

export interface RecommendedMentor {
  employee_id: string;
  name: string;
  designation: string;
  match_score: number;
  skills: string[];
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


const mockMentors: RecommendedMentor[] = [
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

const initialBatches: StudentBatch[] = [
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
    trainer_ids: 'emp-101',
    trainer_name: 'Dr. Sarah Jenkins',
    status: 'open',
    delivery_mode: 'hybrid'
  }
];

export const TrainingManagement: React.FC = () => {
  const [mainTab, setMainTab] = useState<'engagements' | 'student_batch'>('engagements');
  const [typeFilter, setTypeFilter] = useState<EngagementTypeFilter>('all');
  const [subTab, setSubTab] = useState<'list' | 'allocation'>('list');

  const [batches, setBatches] = useState<StudentBatch[]>(initialBatches);
  
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
  const [newMode, setNewMode] = useState('');
  const [newDom, setNewDom] = useState('');

  // Initialize with empty arrays instead of hardcoded mock records
  const [engagements, setEngagements] = useState<TrainingEngagement[]>([]);
  const [selectedEngagementId, setSelectedEngagementId] = useState<string>('');
  const [recommendedMentors, setRecommendedMentors] = useState<RecommendedMentor[]>([]);

  // 1. Fetch real engagements on initial render and auto-select the first valid record
  useEffect(() => {
    fetch('/api/training/engagements')
      .then((res) => (res.ok ? res.json() : []))
      .then((data: TrainingEngagement[]) => {
        setEngagements(data);
        if (data.length > 0) {
          // Dynamically sets selected ID to an existing record (e.g., 'rp2-train-0001')
          setSelectedEngagementId(data[0].engagement_id);
        }
      })
      .catch((err) => console.error('Failed to load engagements:', err));
  }, []);

  // 2. Safely compute current selected engagement
  const selectedEngagement = 
    engagements.find((e) => e.engagement_id === selectedEngagementId) || engagements[0];

  // 3. Fetch recommendations only when a valid selectedEngagementId exists
  useEffect(() => {
    if (!selectedEngagementId) return;

    fetch(`/api/training/engagements/${selectedEngagementId}/recommendations`)
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => setRecommendedMentors(data))
      .catch((err) => console.error('Failed to fetch recommendations:', err));
  }, [selectedEngagementId]);
  const filteredEngagements = engagements.filter((e) => {
    if (typeFilter === 'all') return true;
    return e.engagement_type === typeFilter;
  });

  useEffect(() => {
    if (selectedEngagement) {
      fetch(`/api/training/engagements/${selectedEngagement.engagement_id}/recommendations`)
        .then((res) => (res.ok ? res.json() : mockMentors))
        .then((data) => setRecommendedMentors(data))
        .catch(() => setRecommendedMentors(mockMentors));
    }
  }, [selectedEngagementId]);

  const handleProposeMentor = async (engagementId: string, mentor: RecommendedMentor) => {
    setEngagements((prev) =>
      prev.map((e) =>
        e.engagement_id === engagementId
          ? { ...e, status: 'proposed', mentor_id: mentor.employee_id, mentor_name: mentor.name }
          : e
      )
    );

    try {
      await fetch(`/api/training/engagements/${engagementId}/propose`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mentor_id: mentor.employee_id }),
      });
    } catch (err) {
      console.warn('Backend proposal request fallback to state update', err);
    }
  };

  const handleConfirmAllocation = async (engagementId: string) => {
    setEngagements((prev) =>
      prev.map((e) => (e.engagement_id === engagementId ? { ...e, status: 'allocated' } : e))
    );

    try {
      await fetch(`/api/training/engagements/${engagementId}/confirm`, { method: 'POST' });
    } catch (err) {
      console.warn('Backend confirmation fallback to state update', err);
    }
  };

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
      location: newLoc,
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
      await fetch('/api/training/engagements', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: newTitle,
          engagement_type: newType,
          start_date: newStartDate,
          end_date: newEndDate,
          required_hours: newHours,
          description: newDesc,
          location: newLoc,
        })
      });
    } catch (err) {
      console.warn('Backend creation fallback to state update', err);
    }
  };
  
  const fetchStudentBatches = async () => {
  try {
    const res = await fetch('/api/training/student-batches', {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });

    if (res.ok) {
      const data: StudentBatch[] = await res.json();
      setBatches(data);
      return;
    }
  } catch (e) {
    console.warn('Fallback to local state batch list', e);
  }

  // Fallback initial state if API endpoint is unreachable
  const defaultBatches: StudentBatch[] = [
    {
      batch_id: 'rp2-batch-0100',
      batch_name: 'Batch-Sep-Oct-2026',
      domain: 'Data Analytics',
      start_date: '2026-09-15',
      end_date: '2026-10-15',
      trainer_ids: 'emp-102',
      trainer_name: 'Alex Morgan',
    
      status: 'open',
      delivery_mode: 'online'
    },
  ];
  setBatches(defaultBatches);
};

useEffect(() => {
  fetchStudentBatches();
}, []);

  const handleAutoGenerateBatch = async () => {
    try {
      const res = await fetch('/api/training/student-batches/auto-generate-next', { method: 'POST' });
      if (res.ok) {
        const generated = await res.json();
        setBatches([generated, ...batches]);
        return;
      }
    } catch (e) {
      console.warn('Fallback to local state batch generation');
    }

    const nextBatchId = `rp2-batch-${String(batches.length + 100).padStart(4, '0')}`;
    const newBatch: StudentBatch = {
      batch_id: nextBatchId,
      batch_name: 'Batch-Sep-Oct-2026',
      domain: 'Data Analytics',
      start_date: '2026-09-15',
      end_date: '2026-10-15',
      trainer_ids: 'emp-102',
      trainer_name: 'Alex Morgan',
      status: 'open',
      delivery_mode: 'online'
    };
    setBatches([newBatch, ...batches]);
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
            <button
              onClick={() => setIsModalOpen(true)}
              className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-2.5 rounded-xl flex items-center gap-2 shadow-lg transition-all"
            >
              <Plus className="w-4 h-4" /> Schedule Engagement
            </button>
          ) : (
            <button
              onClick={handleAutoGenerateBatch}
              className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold px-4 py-2.5 rounded-xl flex items-center gap-2 shadow-lg transition-all"
            >
              <RefreshCw className="w-4 h-4" /> Auto-Generate Next Batch
            </button>
          )}
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

          {subTab === 'list' && (
            <Card title="Training Engagements">
              <div className="space-y-3">
                {filteredEngagements.map((item) => (
                  <div
                    key={item.engagement_id}
                    className="p-4 bg-slate-950 border border-slate-800 rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-4 transition-all hover:border-slate-700"
                  >
                    <div className="flex items-start gap-3">
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
                ))}
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
                              {mentor.skills.map((skill, i) => (
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

      {mainTab === 'student_batch' && (
  <Card title="Student Batches">
    {/* Header / Action Bar */}
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
      <div className="p-4 bg-indigo-950/20 border border-indigo-500/30 rounded-xl flex items-start gap-3 flex-1">
        <AlertCircle className="w-5 h-5 text-indigo-400 mt-0.5 shrink-0" />
        <div className="text-xs text-slate-300 leading-relaxed">
          <span className="font-bold text-indigo-300">Round-Robin Allocation:</span> Student batches use round-robin rotation to assign mentors sequentially across monthly cycles without skill requirement matching tables.
        </div>
      </div>

      {typeof handleAutoGenerateBatch === 'function' && (
        <button
          onClick={handleAutoGenerateBatch}
          className="shrink-0 px-3.5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl flex items-center justify-center gap-2 transition-all shadow-sm"
        >
          <Plus className="w-4 h-4" />
          Auto-Generate Batch
        </button>
      )}
    </div>

    {/* Batches List */}
    <div className="space-y-3">
      {batches.length === 0 ? (
        <div className="p-8 text-center text-xs text-slate-400 bg-slate-950 border border-slate-800 rounded-xl">
          No student batches found.
        </div>
      ) : (
        batches.map((batch) => (
          <div
            key={batch.batch_id}
            className="p-4 bg-slate-950 border border-slate-800 rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-4 transition-all hover:border-slate-700"
          >
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

            {/* Mentor & Designation Card */}
            <div className="flex flex-col items-start md:items-end bg-slate-900 border border-slate-800 px-3.5 py-2 rounded-lg shrink-0">
              <span className="text-[10px] uppercase tracking-wider text-slate-400 font-medium">Assigned Mentor</span>
              <span className="text-xs font-bold text-indigo-400 mt-0.5">
                {batch.trainer_name || batch.trainer_ids || 'Unassigned'}
              </span>
              
            </div>
          </div>
        ))
      )}
    </div>
  </Card>
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
                    onChange={(e) => setNewDom(e.target.value)}
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
                    onChange={(e) => setNewMode(e.target.value)}
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
                    onChange={(e) => setNewAud(e.target.value)}
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
        </div>
      )}
    </div>
  );
};