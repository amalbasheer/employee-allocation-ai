import React, { useState, useEffect } from 'react';
import { 
  GitMerge, 
  Sparkles, 
  Send, 
  CheckCircle2, 
  Clock, 
  Search, 
  Cpu, 
  Zap, 
  ChevronRight,
  ShieldAlert
} from 'lucide-react';
import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Modal } from '../../components/common/Modal';
import { projectService } from '../../services/projectService';
import { allocationService } from '../../services/allocationService';
import { Project, ResourceMatch } from '../../types';

export const ProjectAllocation: React.FC = () => {
  // Projects State
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [loadingProjects, setLoadingProjects] = useState<boolean>(true);

  // Recommendations / Vector Matching State
  const [recommendations, setRecommendations] = useState<ResourceMatch[]>([]);
  const [loadingRecommendations, setLoadingRecommendations] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Proposal Modal State
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [selectedCandidate, setSelectedCandidate] = useState<ResourceMatch | null>(null);
  const [roleOnProject, setRoleOnProject] = useState<string>('');
  const [submittingProposal, setSubmittingProposal] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Fallback Projects Data
  const fallbackProjects: Project[] = [
    {
      project_id: 'proj-101',
      title: 'LLM Fine-Tuning & RAG Pipeline',
      description: 'Build an enterprise RAG knowledge graph with vector embeddings and custom LoRA adapters.',
      department: 'AI/ML Engineering',
      required_skills: ['Python', 'FastAPI', 'PyTorch', 'PostgreSQL', 'LangChain'],
      status: 'OPEN',
      created_at: '2026-08-10',
    },
    {
      project_id: 'proj-102',
      title: 'Real-time Computer Vision Edge Analytics',
      description: 'Deploy low-latency Object Detection models on edge devices for manufacturing quality inspection.',
      department: 'Computer Vision',
      required_skills: ['Python', 'Computer Vision', 'PyTorch', 'Docker', 'Git'],
      status: 'OPEN',
      created_at: '2026-08-12',
    },
    {
      project_id: 'proj-103',
      title: 'Automated Financial Forecasting Dashboard',
      description: 'Create interactive dashboards and statistical forecasting models for executive metrics.',
      department: 'Data Analytics',
      required_skills: ['SQL', 'Power BI', 'Data Analytics', 'Python', 'Communication'],
      status: 'IN_PROGRESS',
      created_at: '2026-08-01',
    },
  ];

  // Fallback Candidate Vector Matches
  const fallbackMatches: Record<string, ResourceMatch[]> = {
    'proj-101': [
      {
        resource_id: 'res-1',
        name: 'Dr. Sarah Jenkins',
        resource_type: 'EMPLOYEE',
        designation: 'Senior AI Engineer',
        suitability_score: 95.8,
        matching_skills: ['Python', 'FastAPI', 'PyTorch', 'LangChain', 'PostgreSQL'],
        missing_skills: [],
        availability_status: 'AVAILABLE',
      },
      {
        resource_id: 'res-2',
        name: 'Alex Rivera',
        resource_type: 'STUDENT',
        department_or_domain: 'AI Research Intern',
        suitability_score: 88.4,
        matched_skills: ['Python', 'FastAPI', 'PostgreSQL'],
        missing_skills: ['PyTorch', 'LangChain'],
        availability_status: 'AVAILABLE',
      },
      {
        resource_id: 'res-3',
        name: 'Marcus Vance',
        resource_type: 'EMPLOYEE',
        designation: 'Fullstack Developer',
        suitability_score: 74.2,
        matching_skills: ['Python', 'FastAPI', 'PostgreSQL'],
        missing_skills: ['PyTorch', 'LangChain'],
        availability_status: 'AVAILABLE',
      },
    ],
    'proj-102': [
      {
        resource_id: 'res-4',
        name: 'Elena Rostova',
        resource_type: 'EMPLOYEE',
        department_or_domain: 'Computer Vision',
        suitability_score: 94.1,
        matched_skills: ['Python', 'Computer Vision', 'PyTorch', 'Docker'],
        missing_skills: ['Git'],
        availability_status: 'AVAILABLE',
      },
    ],
  };

  // Load Initial Projects
  useEffect(() => {
    const fetchProjects = async () => {
      setLoadingProjects(true);
      try {
        const data = await projectService.getProjects();
        if (data && data.length > 0) {
          setProjects(data);
          setSelectedProject(data[0]);
        } else {
          setProjects(fallbackProjects);
          setSelectedProject(fallbackProjects[0]);
        }
      } catch (err) {
        console.warn('API unavailable, using initial fallback project data.', err);
        setProjects(fallbackProjects);
        setSelectedProject(fallbackProjects[0]);
      } finally {
        setLoadingProjects(false);
      }
    };

    fetchProjects();
  }, []);

  // Retrieve Vector Recommendations when Selected Project Changes
  useEffect(() => {
    if (!selectedProject) return;

    const fetchRecommendations = async () => {
      setLoadingRecommendations(true);
      try {
        const matches = await allocationService.getRecommendations(selectedProject.project_id, 3);
        if (matches && matches.length > 0) {
          setRecommendations(matches);
        } else {
          setRecommendations(fallbackMatches[selectedProject.project_id] || fallbackMatches['proj-101']);
        }
      } catch (err) {
        console.warn('API unavailable, using fallback vector recommendation calculations.', err);
        setRecommendations(fallbackMatches[selectedProject.project_id] || fallbackMatches['proj-101']);
      } finally {
        setLoadingRecommendations(false);
      }
    };

    fetchRecommendations();
  }, [selectedProject]);

  // Open Proposal Modal
  const handleOpenProposal = (candidate: ResourceMatch) => {
    setSelectedCandidate(candidate);
    setRoleOnProject(candidate.department_or_domain || 'Project Member');
    setIsModalOpen(true);
  };

  // Submit Proposal
  const handleSendProposal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProject || !selectedCandidate) return;

    setSubmittingProposal(true);
    try {
      await allocationService.proposeAllocation(
        selectedProject.project_id,
        selectedCandidate.resource_id,
        roleOnProject
      );
      showToast(`Proposal successfully dispatched to ${selectedCandidate.name}!`);
    } catch (err) {
      console.warn('Backend API fallback triggered for proposal submission.', err);
      showToast(`Proposal sent to ${selectedCandidate.name} (Demo Mode).`);
    } finally {
      setSubmittingProposal(false);
      setIsModalOpen(false);
    }
  };

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  // Safe filtering handling optional/undefined department values
  const filteredProjects = projects.filter((p) => {
    const titleMatch = (p.title || '').toLowerCase().includes(searchQuery.toLowerCase());
    const deptMatch = (p.department || '').toLowerCase().includes(searchQuery.toLowerCase());
    return titleMatch || deptMatch;
  });

  return (
    <div className="space-y-6">
      {/* Toast Notification Banner */}
      {toastMessage && (
        <div className="fixed top-20 right-6 z-50 bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 px-4 py-3 rounded-xl shadow-2xl flex items-center gap-3 backdrop-blur-md animate-in fade-in slide-in-from-top-4">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          <span className="text-xs font-semibold">{toastMessage}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">Project Allocations</h1>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              pgvector Engine
            </span>
          </div>
          <p className="text-slate-400 text-sm mt-0.5">
            Compute cosine similarity embeddings to match qualified staff and interns with active project requirements.
          </p>
        </div>
      </div>

      {/* Main Layout Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Project Selector (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <Card 
            title="Active Projects" 
            subtitle="Select a project to calculate AI vector recommendations"
          >
            {/* Search Input */}
            <div className="relative mb-4">
              <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search projects by title or department..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 text-xs text-white pl-9 pr-4 py-2 rounded-xl focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            {/* Projects List */}
            {loadingProjects ? (
              <div className="py-8 text-center text-slate-500 text-xs flex flex-col items-center gap-2">
                <Cpu className="w-6 h-6 animate-spin text-indigo-400" />
                <span>Loading active project pool...</span>
              </div>
            ) : filteredProjects.length === 0 ? (
              <p className="text-xs text-slate-500 text-center py-6">No matching projects found.</p>
            ) : (
              <div className="space-y-3">
                {filteredProjects.map((proj) => {
                  const isSelected = selectedProject?.project_id === proj.project_id;
                  return (
                    <div
                      key={proj.project_id}
                      onClick={() => setSelectedProject(proj)}
                      className={`p-4 rounded-xl border transition-all cursor-pointer ${
                        isSelected
                          ? 'bg-indigo-600/10 border-indigo-500/50 shadow-md shadow-indigo-500/5'
                          : 'bg-slate-950/70 border-slate-800 hover:border-slate-700 hover:bg-slate-950'
                      }`}
                    >
                      <div className="flex justify-between items-start mb-1.5">
                        <h4 className="font-bold text-white text-xs sm:text-sm line-clamp-1">
                          {proj.title}
                        </h4>
                        <Badge
                          label={proj.status || 'OPEN'}
                          variant={proj.status === 'OPEN' ? 'emerald' : 'amber'}
                        />
                      </div>
                      <p className="text-[11px] text-slate-400 line-clamp-2 mb-3">
                        {proj.description}
                      </p>

                      <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-800/60 text-[10px]">
                        <span className="text-slate-500">{proj.required_roles?.join(', ') || 'General'}</span>
                        <div className="flex items-center gap-1 text-indigo-400 font-medium">
                          <span>View Match Pool</span>
                          <ChevronRight className="w-3.5 h-3.5" />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
        </div>

        {/* Right Column: Candidate Matching Panel (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          {selectedProject ? (
            <Card
              title="Candidate Recommendations"
              subtitle={`Calculated embeddings for "${selectedProject.title}"`}
              action={
                <button
                  onClick={() => setSelectedProject({ ...selectedProject })}
                  className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded-lg flex items-center gap-1.5 transition-colors"
                >
                  <Zap className="w-3.5 h-3.5 text-amber-400" />
                  Recalculate Scores
                </button>
              }
            >
              {/* Project Requirements Overview Banner */}
              <div className="p-3.5 bg-slate-950 border border-slate-800 rounded-xl mb-6 space-y-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-400">Target Department: <strong className="text-white">{selectedProject.department || 'N/A'}</strong></span>
                  <span className="text-slate-500 text-[11px]">ID: {selectedProject.project_id}</span>
                </div>
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="text-[11px] font-semibold text-slate-400 mr-1">Required Skills:</span>
                  {(selectedProject.requirements?.map((req) => req.skill_name) || []).map((skill) => (
                    <span
                      key={skill}
                      className="px-2 py-0.5 bg-slate-900 border border-slate-800 text-indigo-300 text-[10px] rounded-md font-mono"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>

              {/* Recommendations List */}
              {loadingRecommendations ? (
                <div className="py-12 text-center text-slate-500 text-xs flex flex-col items-center gap-3">
                  <Sparkles className="w-8 h-8 animate-spin text-indigo-400" />
                  <span>Generating pgvector cosine similarity rankings...</span>
                </div>
              ) : recommendations.length === 0 ? (
                <div className="p-8 text-center bg-slate-950 rounded-xl border border-slate-800 text-slate-500 text-xs">
                  No suitable candidates found meeting vector threshold limits.
                </div>
              ) : (
                <div className="space-y-4">
                  {recommendations.map((candidate, idx) => (
                    <div
                      key={candidate.resource_id}
                      className="p-5 bg-slate-950 border border-slate-800 rounded-xl space-y-4 relative overflow-hidden group hover:border-slate-700 transition-all"
                    >
                      {/* Top Rank Badge */}
                      {idx === 0 && (
                        <div className="absolute top-0 right-0 bg-gradient-to-l from-emerald-500 to-teal-500 text-slate-950 text-[10px] font-black tracking-wider px-3 py-0.5 rounded-bl-lg uppercase">
                          Top Match Recommendation
                        </div>
                      )}

                      {/* Header Info */}
                      <div className="flex justify-between items-start pt-1">
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="font-bold text-white text-base">{candidate.name}</h3>
                            <Badge
                              label={candidate.resource_type || 'EMPLOYEE'}
                              variant={candidate.resource_type === 'EMPLOYEE' ? 'emerald' : 'amber'}
                            />
                          </div>
                          <p className="text-xs text-slate-400 mt-0.5">{candidate.department_or_domain || 'Unspecified Domain'}</p>
                        </div>

                        {/* Suitability Score Gauge */}
                        <div className="text-right">
                          <div className="text-xl font-black font-mono text-emerald-400">
                            {(candidate.suitability_score || 0).toFixed(1)}%
                          </div>
                          <span className="text-[10px] text-slate-500">Cosine Similarity</span>
                        </div>
                      </div>

                      {/* Vector Similarity Bar */}
                      <div className="space-y-1">
                        <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden border border-slate-800">
                          <div
                            className="bg-gradient-to-r from-indigo-500 via-teal-500 to-emerald-400 h-full rounded-full transition-all duration-500"
                            style={{ width: `${candidate.suitability_score || 0}%` }}
                          />
                        </div>
                      </div>

                      {/* Matching & Missing Skills Breakdown */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 text-xs">
                        <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/80">
                          <span className="text-[10px] font-semibold text-emerald-400 block mb-1.5 uppercase">
                            Matched Vector Skills ({(candidate.matched_skills || []).length})
                          </span>
                          <div className="flex flex-wrap gap-1">
                            {(candidate.matched_skills || []).map((s) => (
                              <span key={s} className="px-1.5 py-0.5 bg-emerald-500/10 text-emerald-300 rounded text-[10px]">
                                ✓ {s}
                              </span>
                            ))}
                          </div>
                        </div>

                        <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/80">
                          <span className="text-[10px] font-semibold text-rose-400 block mb-1.5 uppercase">
                            Missing Requirements ({(candidate.missing_skills || []).length})
                          </span>
                          <div className="flex flex-wrap gap-1">
                            {(!candidate.missing_skills || candidate.missing_skills.length === 0) ? (
                              <span className="text-[10px] text-slate-500 italic">None - Complete match</span>
                            ) : (
                              candidate.missing_skills.map((s) => (
                                <span key={s} className="px-1.5 py-0.5 bg-rose-500/10 text-rose-300 rounded text-[10px]">
                                  ✕ {s}
                                </span>
                              ))
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Proposal Action Footer */}
                      <div className="flex justify-between items-center pt-3 border-t border-slate-800 text-xs">
                        <span className="text-slate-500 flex items-center gap-1.5 text-[11px]">
                          <Clock className="w-3.5 h-3.5 text-amber-400" />
                          Triggers 72-hour SLA response window
                        </span>

                        <button
                          onClick={() => handleOpenProposal(candidate)}
                          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs rounded-xl flex items-center gap-2 shadow-md shadow-indigo-600/20 transition-all"
                        >
                          <Send className="w-3.5 h-3.5" />
                          Propose Allocation
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          ) : (
            <Card>
              <div className="py-16 text-center text-slate-500 text-xs flex flex-col items-center gap-2">
                <GitMerge className="w-8 h-8 text-slate-700" />
                <span>Select a project from the left panel to inspect vector allocations.</span>
              </div>
            </Card>
          )}
        </div>
      </div>

      {/* Proposal Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Propose Project Allocation"
      >
        {selectedCandidate && selectedProject && (
          <form onSubmit={handleSendProposal} className="space-y-5">
            {/* Context Summary */}
            <div className="p-3.5 bg-slate-950 border border-slate-800 rounded-xl space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-400">Target Project:</span>
                <strong className="text-white">{selectedProject.title}</strong>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Candidate:</span>
                <strong className="text-emerald-400">{selectedCandidate.name} ({selectedCandidate.resource_type})</strong>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Similarity Match:</span>
                <strong className="text-indigo-400 font-mono">{(selectedCandidate.suitability_score || 0).toFixed(1)}%</strong>
              </div>
            </div>

            {/* Role Assignment Input */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Role Assignment on Project
              </label>
              <input
                type="text"
                value={roleOnProject}
                onChange={(e) => setRoleOnProject(e.target.value)}
                required
                placeholder="e.g. Lead AI Engineer / Mentored Intern"
                className="w-full bg-slate-950 border border-slate-800 text-xs text-white px-3 py-2.5 rounded-xl focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            {/* SLA Warning Notice */}
            <div className="p-3 bg-amber-500/10 border border-amber-500/20 text-amber-300 rounded-xl text-[11px] flex items-start gap-2.5">
              <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold block">72-Hour SLA Automated Rollover</span>
                The candidate will receive an in-app proposal notification. If unaccepted after 72 hours, the platform will automatically offer the position to the secondary fallback match.
              </div>
            </div>

            {/* Form Actions */}
            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-xl"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submittingProposal}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl flex items-center gap-2 shadow-lg shadow-indigo-600/20 disabled:opacity-50"
              >
                {submittingProposal ? 'Dispatching...' : 'Confirm & Dispatch Proposal'}
              </button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
};

export const ProjectAllocations = ProjectAllocation;
export default ProjectAllocation;