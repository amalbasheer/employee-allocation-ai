import React from 'react';
import { FolderGit2, User, Sparkles, Clock } from 'lucide-react';

export interface StudentProject {
  id: string;
  title: string;
  category: string;
  role: string;
  mentor: string;
  status: 'active' | 'completed' | 'pending';
  description: string;
  matchScore: number;
  techStack: string[];
  progressPercentage: number;
  startDate: string;
  dueDate: string;
}

const mockProjects: StudentProject[] = [
  {
    id: 'proj-1',
    title: 'Enterprise Search & RAG System',
    category: 'Internal AI Platform',
    role: 'AI & Backend Intern',
    mentor: 'Dr. Sarah Jenkins',
    status: 'active',
    description: 'Building an internal search tool utilizing dense vector embeddings, pgvector index tuning, and FastAPI endpoints for real-time document query processing.',
    matchScore: 94.2,
    techStack: ['PyTorch', 'pgvector', 'FastAPI', 'Python'],
    progressPercentage: 68,
    startDate: 'Aug 01, 2026',
    dueDate: 'Oct 15, 2026',
  },
  {
    id: 'proj-2',
    title: 'Automated LLM Evaluation Pipeline',
    category: 'ML Infrastructure',
    role: 'MLOps Intern',
    mentor: 'Marcus Vance',
    status: 'completed',
    description: 'Engineered automated regression benchmarks and toxicity filters for domain-specific LoRA adapters deployed via Docker and MLflow containerization.',
    matchScore: 89.5,
    techStack: ['Python', 'Docker', 'MLflow', 'PostgreSQL'],
    progressPercentage: 100,
    startDate: 'Jun 01, 2026',
    dueDate: 'Jul 30, 2026',
  },
  {
    id: 'proj-3',
    title: 'Real-time Vector Ingestion Service',
    category: 'Data Engineering',
    role: 'Backend Intern',
    mentor: 'Pending Assignment',
    status: 'pending',
    description: 'Upcoming allocation focused on high-throughput Kafka event streaming and index synchronization into a distributed Qdrant vector database.',
    matchScore: 91.0,
    techStack: ['Kafka', 'Go', 'Qdrant', 'gRPC'],
    progressPercentage: 0,
    startDate: 'Sep 01, 2026',
    dueDate: 'Nov 30, 2026',
  },
];

const StudentDashboard: React.FC = () => {
  const activeCount = mockProjects.filter((p) => p.status === 'active').length;
  const completedCount = mockProjects.filter((p) => p.status === 'completed').length;

  return (
    <div className="w-full max-w-7xl mx-auto space-y-6 p-4 sm:p-6 text-slate-100">
      {/* Header */}
      <div className="border-b border-slate-800 pb-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Intern Dashboard</h1>
          <p className="text-slate-400 text-xs sm:text-sm mt-1">
            View your allocated projects, current progress, assigned mentors, and match metrics.
          </p>
        </div>

        {/* Quick Metrics */}
        <div className="flex gap-3 self-start sm:self-auto">
          <div className="bg-slate-900 border border-slate-800 px-3.5 py-2 rounded-xl text-center">
            <span className="text-[10px] text-slate-400 font-bold uppercase block">Active</span>
            <span className="text-base font-bold text-emerald-400 font-mono">{activeCount}</span>
          </div>
          <div className="bg-slate-900 border border-slate-800 px-3.5 py-2 rounded-xl text-center">
            <span className="text-[10px] text-slate-400 font-bold uppercase block">Completed</span>
            <span className="text-base font-bold text-indigo-400 font-mono">{completedCount}</span>
          </div>
        </div>
      </div>

      {/* Main Container */}
      <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-5 sm:p-6 space-y-4">
        <h2 className="text-lg font-bold text-white mb-4">
          Assigned Projects ({mockProjects.length})
        </h2>

        <div className="space-y-4">
          {mockProjects.map((project) => (
            <div
              key={project.id}
              className={`p-5 bg-slate-950 border rounded-xl space-y-4 transition-all ${
                project.status === 'active'
                  ? 'border-indigo-500/30 shadow-md shadow-indigo-950/10'
                  : 'border-slate-800 opacity-90'
              }`}
            >
              {/* Header & Status */}
              <div className="flex justify-between items-start gap-3">
                <div>
                  <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider">
                    {project.category}
                  </span>
                  <h3 className="text-base font-bold text-white mt-0.5 flex items-center gap-2">
                    <FolderGit2 className="w-4 h-4 text-indigo-400" />
                    {project.title}
                  </h3>
                  <p className="text-xs text-slate-400 font-medium mt-0.5">{project.role}</p>
                </div>

                {/* Status Badge */}
                <span
                  className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${
                    project.status === 'active'
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                      : project.status === 'completed'
                      ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20'
                      : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                  }`}
                >
                  {project.status === 'active'
                    ? 'Active'
                    : project.status === 'completed'
                    ? 'Completed'
                    : 'Pending Onboarding'}
                </span>
              </div>

              {/* Description */}
              <p className="text-xs text-slate-300 leading-relaxed">
                {project.description}
              </p>

              {/* Progress Bar */}
              <div className="space-y-1">
                <div className="flex justify-between text-[11px]">
                  <span className="text-slate-400 font-medium">Completion Progress</span>
                  <span className="text-indigo-400 font-mono font-bold">
                    {project.progressPercentage}%
                  </span>
                </div>
                <div className="w-full h-1.5 bg-slate-900 rounded-full overflow-hidden border border-slate-800/50">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      project.status === 'completed'
                        ? 'bg-emerald-500'
                        : project.status === 'active'
                        ? 'bg-indigo-500'
                        : 'bg-amber-500'
                    }`}
                    style={{ width: `${project.progressPercentage}%` }}
                  />
                </div>
              </div>

              {/* Tech Stack */}
              <div className="flex flex-wrap gap-1.5 pt-1">
                {project.techStack.map((tech) => (
                  <span
                    key={tech}
                    className="bg-slate-900 text-slate-300 text-[11px] px-2 py-0.5 rounded border border-slate-800 font-mono"
                  >
                    {tech}
                  </span>
                ))}
              </div>

              {/* Card Footer */}
              <div className="pt-3 border-t border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
                <div className="flex flex-wrap items-center gap-4 text-slate-400">
                  <span className="flex items-center gap-1.5 text-slate-300">
                    <User className="w-3.5 h-3.5 text-indigo-400" />
                    Mentor: <strong className="text-white">{project.mentor}</strong>
                  </span>
                  <span className="flex items-center gap-1 text-slate-400 font-mono">
                    <Clock className="w-3.5 h-3.5 text-slate-500" />
                    {project.startDate} - {project.dueDate}
                  </span>
                </div>

                <span className="text-emerald-400 font-mono font-bold flex items-center gap-1">
                  <Sparkles className="w-3 h-3" /> {project.matchScore}% Match Score
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default StudentDashboard;