import React, { useState } from 'react';
import { Card } from '../../components/common/Card';
import { 
  Video, Plus, Clock, CheckCircle2, XCircle, Send, 
  UserCheck, Star, UserPlus, Sliders, ArrowRight
} from 'lucide-react';

export type WebinarStatus = 'UNASSIGNED' | 'PROPOSED' | 'ACCEPTED' | 'REJECTED' | 'ALLOCATED';
export type ActiveTab = 'WEBINARS' | 'ALLOCATION';

export interface Mentor {
  id: string;
  name: string;
  role: string;
  matchScore: number;
  expertise: string[];
}

export interface Webinar {
  id: number;
  title: string;
  date: string;
  status: WebinarStatus;
  proposedMentorId?: string;
  proposedMentorName?: string;
}

const mockMentors: Mentor[] = [
  {
    id: 'm1',
    name: 'Dr. Sarah Jenkins',
    role: 'Principal AI Engineer',
    matchScore: 98,
    expertise: ['PyTorch', 'CUDA', 'Deep Learning'],
  },
  {
    id: 'm2',
    name: 'Alex Morgan',
    role: 'Staff Systems Architect',
    matchScore: 92,
    expertise: ['Distributed Systems', 'Go', 'Kubernetes'],
  },
  {
    id: 'm3',
    name: 'Elena Rostova',
    role: 'Lead Cloud Security Developer',
    matchScore: 86,
    expertise: ['AWS', 'Zero Trust', 'Python'],
  },
];

const initialWebinars: Webinar[] = [
  {
    id: 1,
    title: 'Advanced PyTorch & CUDA Tuning',
    date: 'Aug 24, 2026',
    status: 'ACCEPTED',
    proposedMentorId: 'm1',
    proposedMentorName: 'Dr. Sarah Jenkins',
  },
  {
    id: 2,
    title: 'Building Scalable Microservices with Go',
    date: 'Sep 02, 2026',
    status: 'UNASSIGNED',
  },
  {
    id: 3,
    title: 'Cloud Native Security Fundamentals',
    date: 'Sep 10, 2026',
    status: 'PROPOSED',
    proposedMentorId: 'm3',
    proposedMentorName: 'Elena Rostova',
  },
];

export const WebinarManagement: React.FC = () => {
  const [webinars, setWebinars] = useState<Webinar[]>(initialWebinars);
  const [activeTab, setActiveTab] = useState<ActiveTab>('WEBINARS');
  const [selectedWebinarId, setSelectedWebinarId] = useState<number>(2);

  const selectedWebinar = webinars.find((w) => w.id === selectedWebinarId) || webinars[0];

  // --- Workflow Actions ---
  const handleProposeMentor = (webinarId: number, mentor: Mentor) => {
    setWebinars((prev) =>
      prev.map((w) =>
        w.id === webinarId
          ? {
              ...w,
              status: 'PROPOSED',
              proposedMentorId: mentor.id,
              proposedMentorName: mentor.name,
            }
          : w
      )
    );
  };

  const handleConfirmAllocation = (webinarId: number) => {
    setWebinars((prev) =>
      prev.map((w) => (w.id === webinarId ? { ...w, status: 'ALLOCATED' } : w))
    );
  };

  const handleRePropose = (webinarId: number) => {
    setWebinars((prev) =>
      prev.map((w) =>
        w.id === webinarId
          ? { ...w, status: 'UNASSIGNED', proposedMentorId: undefined, proposedMentorName: undefined }
          : w
      )
    );
  };

  const handleManageSpeaker = (webinarId: number) => {
    setSelectedWebinarId(webinarId);
    setActiveTab('ALLOCATION');
  };

  const renderStatusBadge = (status: WebinarStatus) => {
    switch (status) {
      case 'UNASSIGNED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-800 text-slate-400 border border-slate-700">
            <Clock className="w-3 h-3" /> Unassigned
          </span>
        );
      case 'PROPOSED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Send className="w-3 h-3" /> Proposed
          </span>
        );
      case 'ACCEPTED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <UserCheck className="w-3 h-3" /> Accepted
          </span>
        );
      case 'REJECTED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <XCircle className="w-3 h-3" /> Declined
          </span>
        );
      case 'ALLOCATED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3 h-3" /> Confirmed
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white">Webinar & Workshop Management</h1>
          <p className="text-slate-400 text-sm">Schedule technical workshops and assign speaker mentors.</p>
        </div>
        <button className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-2.5 rounded-xl flex items-center gap-2 shadow-lg transition-all">
          <Plus className="w-4 h-4" /> Schedule Webinar
        </button>
      </div>

      {/* Tabs Bar */}
      <div className="flex border-b border-slate-800 gap-6">
        <button
          onClick={() => setActiveTab('WEBINARS')}
          className={`pb-3 text-sm font-medium flex items-center gap-2 border-b-2 transition-all ${
            activeTab === 'WEBINARS'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Video className="w-4 h-4" /> Available Webinars
        </button>
        <button
          onClick={() => setActiveTab('ALLOCATION')}
          className={`pb-3 text-sm font-medium flex items-center gap-2 border-b-2 transition-all ${
            activeTab === 'ALLOCATION'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Sliders className="w-4 h-4" /> Speaker Allocation & Recommendations
        </button>
      </div>

      {/* TAB 1: WEBINARS LISTING */}
      {activeTab === 'WEBINARS' && (
        <Card title="Scheduled Webinars">
          <div className="space-y-3">
            {webinars.map((webinar) => (
              <div
                key={webinar.id}
                className="p-4 bg-slate-950 border border-slate-800 rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-4 transition-all hover:border-slate-700"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2.5 bg-indigo-500/10 border border-indigo-500/20 rounded-lg text-indigo-400">
                    <Video className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="font-bold text-white text-sm">{webinar.title}</h4>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {webinar.proposedMentorName ? (
                        <>Speaker: <span className="text-slate-200 font-medium">{webinar.proposedMentorName}</span> • </>
                      ) : (
                        <span className="text-amber-400/80 font-medium">No speaker assigned • </span>
                      )}
                      {webinar.date}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  {renderStatusBadge(webinar.status)}
                  <button
                    onClick={() => handleManageSpeaker(webinar.id)}
                    className="bg-slate-900 hover:bg-slate-800 text-slate-200 text-xs font-semibold px-3 py-1.5 rounded-lg border border-slate-700 flex items-center gap-1 transition-all"
                  >
                    Manage Speaker <ArrowRight className="w-3.5 h-3.5 text-indigo-400" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* TAB 2: RECOMMENDED MENTORS & ALLOCATION WORKFLOW */}
      {activeTab === 'ALLOCATION' && (
        <div className="space-y-6">
          <Card title="Speaker Allocation Portal">
            <div className="space-y-6">
              
              {/* Webinar Selector */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 bg-slate-900 border border-slate-800 rounded-xl">
                <div>
                  <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                    Select Webinar
                  </label>
                  <select
                    value={selectedWebinarId}
                    onChange={(e) => setSelectedWebinarId(Number(e.target.value))}
                    className="bg-slate-950 text-white text-sm font-semibold rounded-lg border border-slate-700 px-3 py-2 focus:outline-none focus:border-indigo-500"
                  >
                    {webinars.map((w) => (
                      <option key={w.id} value={w.id}>
                        {w.title} ({w.date})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex items-center gap-3">
                  <span className="text-xs text-slate-400">Current Status:</span>
                  {renderStatusBadge(selectedWebinar.status)}
                </div>
              </div>

              {/* Status Action Banners */}
              {selectedWebinar.status === 'ACCEPTED' && (
                <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-xl flex items-center justify-between">
                  <div>
                    <p className="text-sm font-bold text-blue-300">Speaker Accepted Proposal!</p>
                    <p className="text-xs text-slate-400">{selectedWebinar.proposedMentorName} accepted the request to host this session.</p>
                  </div>
                  <button
                    onClick={() => handleConfirmAllocation(selectedWebinar.id)}
                    className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-all shadow-md"
                  >
                    Confirm Allocation
                  </button>
                </div>
              )}

              {selectedWebinar.status === 'REJECTED' && (
                <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl flex items-center justify-between">
                  <div>
                    <p className="text-sm font-bold text-rose-300">Proposal Declined</p>
                    <p className="text-xs text-slate-400">{selectedWebinar.proposedMentorName} was unable to host this webinar.</p>
                  </div>
                  <button
                    onClick={() => handleRePropose(selectedWebinar.id)}
                    className="bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-all"
                  >
                    Reset & Choose Another
                  </button>
                </div>
              )}

              {/* Recommended Mentors List */}
              <div className="space-y-4 pt-2">
                <h4 className="text-sm font-bold text-white uppercase tracking-wider">
                  Recommended Mentors for <span className="text-indigo-400">{selectedWebinar.title}</span>
                </h4>

                <div className="grid grid-cols-1 gap-3">
                  {mockMentors.map((mentor) => {
                    const isProposed = selectedWebinar.proposedMentorId === mentor.id;

                    return (
                      <div
                        key={mentor.id}
                        className={`p-4 bg-slate-950 border rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-4 transition-all ${
                          isProposed ? 'border-indigo-500/50 bg-indigo-950/10' : 'border-slate-800'
                        }`}
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <h5 className="font-bold text-white text-base">{mentor.name}</h5>
                            <span className="text-xs bg-emerald-500/10 text-emerald-400 font-mono px-2 py-0.5 rounded border border-emerald-500/20 flex items-center gap-1">
                              <Star className="w-3 h-3 fill-emerald-400" /> {mentor.matchScore}% Match
                            </span>
                          </div>
                          <p className="text-xs text-slate-400">{mentor.role}</p>

                          {/* Expertise Tags */}
                          <div className="flex flex-wrap gap-1 pt-1">
                            {mentor.expertise.map((skill, i) => (
                              <span key={i} className="text-[10px] bg-slate-900 text-slate-400 px-2 py-0.5 rounded border border-slate-800">
                                {skill}
                              </span>
                            ))}
                          </div>
                        </div>

                        {/* WORKFLOW ACTION BUTTONS */}
                        <div>
                          {selectedWebinar.status === 'UNASSIGNED' && (
                            <button
                              onClick={() => handleProposeMentor(selectedWebinar.id, mentor)}
                              className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-2 rounded-lg flex items-center gap-1.5 transition-all shadow-md"
                            >
                              <UserPlus className="w-3.5 h-3.5" /> Propose Webinar
                            </button>
                          )}

                          {isProposed && selectedWebinar.status === 'PROPOSED' && (
                            <span className="text-xs text-amber-400 font-medium italic flex items-center gap-1.5 bg-amber-500/10 px-3 py-1.5 rounded-lg border border-amber-500/20">
                              <Clock className="w-3.5 h-3.5" /> Awaiting Response
                            </span>
                          )}

                          {isProposed && selectedWebinar.status === 'ACCEPTED' && (
                            <button
                              onClick={() => handleConfirmAllocation(selectedWebinar.id)}
                              className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-all shadow-md"
                            >
                              Confirm
                            </button>
                          )}

                          {isProposed && selectedWebinar.status === 'ALLOCATED' && (
                            <span className="text-xs text-emerald-400 font-bold flex items-center gap-1.5 bg-emerald-500/10 px-3 py-1.5 rounded-lg border border-emerald-500/20">
                              <CheckCircle2 className="w-3.5 h-3.5" /> Confirmed Speaker
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
        </div>
      )}
    </div>
  );
};