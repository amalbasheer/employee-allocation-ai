import React, { useState, useEffect } from 'react';
import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { 
  UserPlus, 
  Search, 
  Edit2, 
  Trash2, 
  Briefcase, 
  GraduationCap, 
  X, 
  Check,
  Mail,
  Building2,
  Upload,
  Link as LinkIcon,
  FileText,
  Clock,
  Award,
  Crown
} from 'lucide-react';
import api from '../../services/api';

// --- Types Aligned with Database Schemas ---

export interface Designation {
  designation_id: string;
  title: string;
}

export interface CompanyEmployee {
  employee_id: string;
  name: string;
  email: string;
  department: string;
  designation_id: string;
  experience_years: number;
  weekly_capacity_hours: number;
  is_team_lead: boolean;
  created_at?: string;
}

export interface StudentIntern {
  intern_id: string;
  name: string;
  email: string;
  college_institution: string;
  degree_program?: string;
  resume_document_url: string;
  review_status?: string;
  reviewed_by?: string;
  extracted_skills_raw?: string;
  role: string; // 'intern' | 'student'
  current_status: string; // 'AVAILABLE' | 'ALLOCATED' | 'ON_LEAVE'
  created_at?: string;
}

export const UserManagement: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'EMPLOYEE' | 'STUDENT'>('EMPLOYEE');
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(false);

  // Data States
  const [employees, setEmployees] = useState<CompanyEmployee[]>([]);
  const [students, setStudents] = useState<StudentIntern[]>([]);
  //const [designations, setDesignations] = useState<Designation[]>([]);
  const [designations, setDesignations] = useState<any[]>([]);
  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  // Resume Mode for Students: 'URL' or 'FILE'
  const [resumeMode, setResumeMode] = useState<'URL' | 'FILE'>('URL');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);


  // Employee Form State
  const [employeeForm, setEmployeeForm] = useState({
    name: '',
    email: '',
    department: '',
    designation_id: '',
    experience_years: 0,
    weekly_capacity_hours: 40,
    is_team_lead: false,
  });

  // Student Form State
  const [studentForm, setStudentForm] = useState({
    name: '',
    email: '',
    college_institution: '',
    degree_program: '',
    resume_document_url: '',
    role: 'intern',
    current_status: 'AVAILABLE',
    review_status: 'UNVERIFIED',
    reviewed_by: '',
    extracted_skills_raw: '',
  });

  

// Fetch designations on component load
  useEffect(() => {
    const fetchDesignations = async () => {
      try {
        const res = await api.get('/api/taxonomy/designations');
      // If API returns { designations: [...] } use res.data.designations, else res.data
        setDesignations(Array.isArray(res.data) ? res.data : res.data.designations || []);
      } catch (err) {
        console.error('Failed to load designations:', err);
      }
    };

    fetchDesignations();
  }, []);

    

  // Fetch users on component mount or tab change
  useEffect(() => {
    fetchUsers();
  }, [activeTab]);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      if (activeTab === 'EMPLOYEE') {
        const res = await api.get('/api/employees');
        setEmployees(res.data);
      } else {
        const res = await api.get('/api/interns');
        setStudents(res.data);
      }
    } catch (err) {
      console.error('Failed to fetch data, loading mock data fallback', err);
      // Fallback mock data if API endpoint is not yet connected
      if (activeTab === 'EMPLOYEE') {
        setEmployees([
          {
            employee_id: 'e1',
            name: 'Dr. Sarah Jenkins',
            email: 'sarah.jenkins@company.com',
            department: 'AI Research',
            designation_id: 'rp2-des-01',
            experience_years: 6.5,
            weekly_capacity_hours: 40,
            is_team_lead: true,
          },
          {
            employee_id: 'e2',
            name: 'Marcus Vance',
            email: 'marcus.vance@company.com',
            department: 'Software Engineering',
            designation_id: 'rp2-des-02',
            experience_years: 3.0,
            weekly_capacity_hours: 35,
            is_team_lead: false,
          },
        ]);
      } else {
        setStudents([
          {
            intern_id: 's1',
            name: 'Alex Rivera',
            email: 'alex.rivera@university.edu',
            college_institution: 'MIT',
            degree_program: 'B.S. Computer Science',
            resume_document_url: 'https://storage.bucket.com/resumes/alex_rivera.pdf',
            role: 'intern',
            current_status: 'AVAILABLE',
          },
          {
            intern_id: 's2',
            name: 'Elena Rostova',
            email: 'elena.r@stanford.edu',
            college_institution: 'Stanford University',
            degree_program: 'M.S. Data Science',
            resume_document_url: 'https://storage.bucket.com/resumes/elena_rostova.pdf',
            role: 'student',
            current_status: 'ALLOCATED',
          },
        ]);
      }
    } finally {
      setLoading(false);
    }
  };

  // Resolve Designation Title from ID
  const getDesignationTitle = (designationId?: string): string => {
    if (!designationId) return 'N/A';
    const match = designations.find((d) => d.designation_id === designationId);
    return match ? match.title : 'N/A';
  };
  
  // Open Modal for Create
  const handleOpenCreateModal = () => {
    setEditingId(null);
    setSelectedFile(null);
    setResumeMode('URL');

    setEmployeeForm({
      name: '',
      email: '',
      department: '',
      designation_id: designations[0]?.designation_id || '',
      experience_years: 0,
      weekly_capacity_hours: 40,
      is_team_lead: false,
    });

    setStudentForm({
      name: '',
      email: '',
      college_institution: '',
      degree_program: '',
      resume_document_url: '',
      role: 'intern',
      current_status: 'AVAILABLE',
      review_status: 'UNVERIFIED',
      reviewed_by: '',
      extracted_skills_raw: '',
    });

    setIsModalOpen(true);
  };

  // Open Modal for Edit
  const handleOpenEditModal = (item: CompanyEmployee | StudentIntern) => {
    setSelectedFile(null);
    setResumeMode('URL');

    if (activeTab === 'EMPLOYEE') {
      const emp = item as CompanyEmployee;
      setEditingId(emp.employee_id);
      setEmployeeForm({
        name: emp.name,
        email: emp.email,
        department: emp.department,
        designation_id: emp.designation_id || '',
        experience_years: emp.experience_years,
        weekly_capacity_hours: emp.weekly_capacity_hours,
        is_team_lead: emp.is_team_lead,
      });
    } else {
      const std = item as StudentIntern;
      setEditingId(std.intern_id);
      setStudentForm({
        name: std.name,
        email: std.email,
        college_institution: std.college_institution,
        degree_program: std.degree_program || '',
        resume_document_url: std.resume_document_url,
        role: std.role,
        current_status: std.current_status,
        review_status: std.review_status || 'UNVERIFIED',
        reviewed_by: std.reviewed_by || '',
        extracted_skills_raw: std.extracted_skills_raw || '',
      });
    }

    setIsModalOpen(true);
  };
    
  
  const [verifyingId, setVerifyingId] = useState<string | null>(null);

  const handleVerifyStudent = async (internId: string) => {
    try {
      setVerifyingId(internId); // Disable button / show loading
      const res = await api.patch<StudentIntern>(`/api/interns/${internId}/verify`);
    
      setStudents((prev) =>
        prev.map((std) => (std.intern_id === internId ? res.data : std))
      );
    } catch (err) {
      console.error('Failed to verify student:', err);
      alert('Verification failed. Ensure you have admin privileges.');
    } finally {
      setVerifyingId(null); // Re-enable
    }
  };
  


  // Helper to upload file to backend bucket and receive storage URL
  const uploadResumeFile = async (file: File): Promise<string> => {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const res = await api.post('/api/interns/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return res.data.file_url; // Returns generated bucket URL
    } catch {
      // Fallback mockup URL if storage endpoint is not wired up
      return `https://storage.bucket.com/resumes/${Date.now()}_${file.name}`;
    }
  };

  // Save User (Create or Update)
  const handleSaveUser = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      if (activeTab === 'EMPLOYEE') {
        const payload = employeeForm;

        if (editingId) {
          await api.put(`/api/employees/${editingId}`, payload);
          setEmployees((prev) =>
            prev.map((emp) => (emp.employee_id === editingId ? { ...emp, ...payload } : emp))
          );
        } else {
          const res = await api.post('/api/employees', payload);
          const newEmp = res.data || { ...payload, employee_id: `emp_${Date.now()}` };
          setEmployees((prev) => [...prev, newEmp]);
        }
      } else {
        // Handle Resume Upload if FILE mode selected
        let finalResumeUrl = studentForm.resume_document_url;
        if (resumeMode === 'FILE' && selectedFile) {
          finalResumeUrl = await uploadResumeFile(selectedFile);
        }

        const payload = {
          ...studentForm,
          resume_document_url: finalResumeUrl,
        };

        if (editingId) {
          await api.put(`/api/interns/${editingId}`, payload);
          setStudents((prev) =>
            prev.map((std) => (std.intern_id === editingId ? { ...std, ...payload } : std))
          );
        } else {
          const res = await api.post('/api/interns', payload);
          const newStd = res.data || { ...payload, intern_id: `std_${Date.now()}` };
          setStudents((prev) => [...prev, newStd]);
        }
      }

      setIsModalOpen(false);
    } catch (err) {
      console.error('Failed to save record:', err);
      alert('Error saving record. Check console for details.');
    }
  };

  // Delete User
  const handleDeleteUser = async (id: string, name: string) => {
    if (window.confirm(`Are you sure you want to delete ${name}?`)) {
      try {
        if (activeTab === 'EMPLOYEE') {
          await api.delete(`/api/employees/${id}`);
          setEmployees((prev) => prev.filter((e) => e.employee_id !== id));
        } else {
          await api.delete(`/api/interns/${id}`);
          setStudents((prev) => prev.filter((s) => s.intern_id !== id));
        }
      } catch (err) {
        console.error('Failed to delete record:', err);
        // Fallback local UI removal
        if (activeTab === 'EMPLOYEE') {
          setEmployees((prev) => prev.filter((e) => e.employee_id !== id));
        } else {
          setStudents((prev) => prev.filter((s) => s.intern_id !== id));
        }
      }
    }
  };

  // Filtering
  const filteredEmployees = employees.filter(
    (e) =>
      e.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.department.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const filteredStudents = students.filter(
    (s) =>
      s.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.college_institution.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (s.degree_program && s.degree_program.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">User Directory</h1>
          <p className="text-slate-400 text-sm">
            Manage company employees, interns, educational backgrounds, and capacity settings.
          </p>
        </div>

        <button
          onClick={handleOpenCreateModal}
          className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs rounded-xl shadow-lg shadow-indigo-600/20 transition-all self-start sm:self-auto"
        >
          <UserPlus className="w-4 h-4" />
          <span>Add {activeTab === 'EMPLOYEE' ? 'Employee' : 'Student / Intern'}</span>
        </button>
      </div>

      {/* Tabs & Search Controls */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-2 rounded-2xl">
        <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-xl">
          <button
            onClick={() => setActiveTab('EMPLOYEE')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'EMPLOYEE'
                ? 'bg-indigo-600 text-white shadow-md'
                : 'text-slate-400 hover:text-white hover:bg-slate-900'
            }`}
          >
            <Briefcase className="w-4 h-4" />
            <span>Employees</span>
            <span
              className={`ml-1 px-1.5 py-0.5 rounded-full text-[10px] ${
                activeTab === 'EMPLOYEE' ? 'bg-indigo-700 text-white' : 'bg-slate-800 text-slate-400'
              }`}
            >
              {employees.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('STUDENT')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'STUDENT'
                ? 'bg-indigo-600 text-white shadow-md'
                : 'text-slate-400 hover:text-white hover:bg-slate-900'
            }`}
          >
            <GraduationCap className="w-4 h-4" />
            <span>Students & Interns</span>
            <span
              className={`ml-1 px-1.5 py-0.5 rounded-full text-[10px] ${
                activeTab === 'STUDENT' ? 'bg-indigo-700 text-white' : 'bg-slate-800 text-slate-400'
              }`}
            >
              {students.length}
            </span>
          </button>
        </div>

        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder={`Search ${activeTab === 'EMPLOYEE' ? 'employees by name, email, department...' : 'students by name, college, degree...'}`}
            className="w-full bg-slate-950 border border-slate-800 text-xs text-white pl-9 pr-4 py-2 rounded-xl focus:outline-none focus:ring-1 focus:ring-indigo-500 placeholder-slate-500"
          />
        </div>
      </div>

      {/* Database Matched Table View */}
      <Card title={`${activeTab === 'EMPLOYEE' ? 'Company Employees' : 'Interns & Students'} Roster`}>
        <div className="overflow-x-auto">
          {activeTab === 'EMPLOYEE' ? (
            /* EMPLOYEES TABLE */
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950 text-slate-400 uppercase font-semibold border-b border-slate-800">
                <tr>
                  <th className="p-3">Employee Name</th>
                  <th className="p-3">Department</th>
                  <th className="p-3">Experience</th>
                  <th className="p-3">Weekly Capacity</th>
                  <th className="p-3">Role Type</th>
                  <th className="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredEmployees.length > 0 ? (
                  filteredEmployees.map((emp) => (
                    <tr key={emp.employee_id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="p-3">
                        <div className="font-medium text-white flex items-center gap-1.5">
                          {emp.name}
                          {emp.is_team_lead && (
                            <span title="Team Lead">
                              <Crown className="w-3.5 h-3.5 text-amber-400 inline shrink-0" />
                            </span>
                          )}
                        </div>
                        <div className="text-[11px] text-slate-500 flex items-center gap-1">
                          <Mail className="w-3 h-3" />
                          {emp.email}
                        </div>
                      </td>
                      <td className="p-3">
                        <div className="flex items-center gap-1.5 text-slate-300">
                          <Building2 className="w-3.5 h-3.5 text-slate-500" />
                          {emp.department}
                        </div>
                      </td>
                      
                      <td className="p-3">
                        <div className="flex items-center gap-1 text-slate-300">
                          <Award className="w-3.5 h-3.5 text-slate-500" />
                          {emp.experience_years} yrs
                        </div>
                      </td>
                      <td className="p-3">
                        <div className="flex items-center gap-1 text-slate-300">
                          <Clock className="w-3.5 h-3.5 text-slate-500" />
                          {emp.weekly_capacity_hours} hrs/wk
                        </div>
                      </td>
                      <td className="p-3">
                        {emp.is_team_lead ? (
                          <Badge label="TEAM LEAD" variant="amber" />
                        ) : (
                          <Badge label="EMPLOYEE" variant="emerald" />
                        )}
                      </td>
                      <td className="p-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleOpenEditModal(emp)}
                            className="p-1.5 hover:bg-slate-800 text-slate-400 hover:text-indigo-400 rounded-lg transition-colors"
                            title="Edit Employee"
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDeleteUser(emp.employee_id, emp.name)}
                            className="p-1.5 hover:bg-slate-800 text-slate-400 hover:text-red-400 rounded-lg transition-colors"
                            title="Delete Employee"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="p-8 text-center text-slate-500">
                      {loading ? 'Loading employees...' : 'No employees found matching your search.'}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          ) : (
            /* STUDENTS / INTERNS TABLE */
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950 text-slate-400 uppercase font-semibold border-b border-slate-800">
                <tr>
                  <th className="p-3">Candidate</th>
                  <th className="p-3">College / Institution</th>
                  <th className="p-3">Degree Program</th>
                  <th className="p-3">Resume Document</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Review</th>
                  <th className="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredStudents.length > 0 ? (
                  filteredStudents.map((std) => (
                    <tr key={std.intern_id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="p-3">
                        <div className="font-medium text-white">{std.name}</div>
                        <div className="text-[11px] text-slate-500 flex items-center gap-1">
                          <Mail className="w-3 h-3" />
                          {std.email}
                        </div>
                      </td>
                      <td className="p-3 text-slate-300 font-medium">
                        {std.college_institution}
                      </td>
                      <td className="p-3 text-slate-400">
                        {std.degree_program || 'N/A'}
                      </td>
                      <td className="p-3">
                        {std.resume_document_url ? (
                          <a
                            href={std.resume_document_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-indigo-400 hover:text-indigo-300 underline font-medium"
                          >
                            <FileText className="w-3.5 h-3.5" />
                            View Resume
                          </a>
                        ) : (
                          <span className="text-slate-500">No Resume</span>
                        )}
                      </td>
                      <td className="p-3">
                        <span
                          className={`font-semibold text-[10px] px-2 py-0.5 rounded-full inline-block ${
                            std.current_status === 'AVAILABLE'
                              ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/50'
                              : std.current_status === 'ALLOCATED'
                              ? 'bg-amber-950/60 text-amber-400 border border-amber-800/50'
                              : 'bg-slate-800 text-slate-400 border border-slate-700'
                          }`}
                        >
                          {std.current_status}
                        </span>
                      </td>
                      {/* Review Status Column (DB Driven) */}
                      <td className="p-3">
                        <div className="flex flex-col gap-1 items-start">
                          {std.review_status?.toUpperCase() === 'VERIFIED' ? (
                            /* Verified State in DB */
                            <div className="flex flex-col gap-0.5">
                              <span className="font-semibold text-[10px] px-2 py-0.5 rounded-full inline-block w-fit bg-emerald-950/60 text-emerald-400 border border-emerald-800/50">
                                VERIFIED
                              </span>
                              <span className="text-[9px] text-slate-400 pl-0.5">
                                Verified by {std.reviewed_by || 'Admin'}
                              </span>
                            </div>
                          ) : (
                            /* Unverified / Newly Added Intern from DB */
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-[10px] px-2 py-0.5 rounded-full inline-block bg-rose-950/60 text-rose-400 border border-rose-800/50 uppercase">
                                {std.review_status || 'UNVERIFIED'}
                              </span>
                              <button
                                type="button"
                                disabled={verifyingId === std.intern_id}
                                onClick={() => handleVerifyStudent(std.intern_id)}
                                className="px-2 py-0.5 text-[10px] font-semibold bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-md shadow-sm transition-all flex items-center gap-1 active:scale-95 cursor-pointer"
                              >
                                <Check className="w-3 h-3" />
                                {verifyingId === std.intern_id ? 'Verifying...' : 'Verify'}
                              </button>
                            </div>
                          )}
                        </div>
                      </td>  
                      <td className="p-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleOpenEditModal(std)}
                            className="p-1.5 hover:bg-slate-800 text-slate-400 hover:text-indigo-400 rounded-lg transition-colors"
                            title="Edit Student"
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDeleteUser(std.intern_id, std.name)}
                            className="p-1.5 hover:bg-slate-800 text-slate-400 hover:text-red-400 rounded-lg transition-colors"
                            title="Delete Student"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="p-8 text-center text-slate-500">
                      {loading ? 'Loading candidates...' : 'No candidate records found matching your search.'}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </Card>

      {/* Modal Dialog for Add/Edit */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-6">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                {editingId ? <Edit2 className="w-5 h-5 text-indigo-400" /> : <UserPlus className="w-5 h-5 text-indigo-400" />}
                {editingId
                  ? `Edit ${activeTab === 'EMPLOYEE' ? 'Employee' : 'Student / Intern'}`
                  : `Add New ${activeTab === 'EMPLOYEE' ? 'Employee' : 'Student / Intern'}`}
              </h2>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveUser} className="space-y-4">
              {/* Common Fields */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Full Name *</label>
                  <input
                    type="text"
                    required
                    value={activeTab === 'EMPLOYEE' ? employeeForm.name : studentForm.name}
                    onChange={(e) =>
                      activeTab === 'EMPLOYEE'
                        ? setEmployeeForm({ ...employeeForm, name: e.target.value })
                        : setStudentForm({ ...studentForm, name: e.target.value })
                    }
                    placeholder="e.g. Sarah Jenkins"
                    className="w-full bg-slate-950 border border-slate-800 text-xs text-white px-3 py-2.5 rounded-xl focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Email Address *</label>
                  <input
                    type="email"
                    required
                    value={activeTab === 'EMPLOYEE' ? employeeForm.email : studentForm.email}
                    onChange={(e) =>
                      activeTab === 'EMPLOYEE'
                        ? setEmployeeForm({ ...employeeForm, email: e.target.value })
                        : setStudentForm({ ...studentForm, email: e.target.value })
                    }
                    placeholder="e.g. sarah.da@rp2.com"
                    className="w-full bg-slate-950 border border-slate-800 text-xs text-white px-3 py-2.5 rounded-xl focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              </div>

              {/* EMPLOYEE Specific Database Schema Fields */}
              {activeTab === 'EMPLOYEE' && (
                <>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">Department *</label>
                      <input
                        type="text"
                        required
                        value={employeeForm.department}
                        onChange={(e) => setEmployeeForm({ ...employeeForm, department: e.target.value })}
                        placeholder="e.g. Data Analytics"
                        className="w-full bg-slate-950 border border-slate-800 text-xs text-white px-3 py-2.5 rounded-xl focus:outline-none focus:ring-1 focus:ring-indigo-500"
                      />
                    </div>
                    
                    {/* Designation Dropdown (Stores designation_id) */}
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">Designation *</label>
                      <select
                        required
                        value={employeeForm.designation_id || ''}
                        onChange={(e) => setEmployeeForm({ ...employeeForm, designation_id: e.target.value })}
                        className="w-full bg-slate-950 border border-slate-800 text-xs text-white px-3 py-2.5 rounded-xl focus:outline-none focus:ring-1 focus:ring-indigo-500 cursor-pointer"
                      >
                        <option value="" disabled className="bg-slate-900 text-slate-500">
                          Select Designation
                        </option>
                        {designations.map((desig) => (
                          <option key={desig.designation_id} value={desig.designation_id} className="bg-slate-900 text-white">
                            {desig.title}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">Experience (Years)</label>
                      <input
                        type="number"
                        step="0.5"
                        min="0"
                        value={employeeForm.experience_years}
                        onChange={(e) =>
                          setEmployeeForm({ ...employeeForm, experience_years: parseFloat(e.target.value) || 0 })
                        }
                        className="w-full bg-slate-950 border border-slate-800 text-xs text-white px-3 py-2.5 rounded-xl focus:outline-none focus:ring-1 focus:ring-indigo-500"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">Weekly Capacity (Hours)</label>
                      <input
                        type="number"
                        min="1"
                        max="80"
                        value={employeeForm.weekly_capacity_hours}
                        onChange={(e) =>
                          setEmployeeForm({ ...employeeForm, weekly_capacity_hours: parseInt(e.target.value) || 40 })
                        }
                        className="w-full bg-slate-950 border border-slate-800 text-xs text-white px-3 py-2.5 rounded-xl focus:outline-none focus:ring-1 focus:ring-indigo-500"
                      />
                    </div>

                    <div className="flex items-center pt-6">
                      <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-slate-300 select-none">
                        <input
                          type="checkbox"
                          checked={employeeForm.is_team_lead}
                          onChange={(e) => setEmployeeForm({ ...employeeForm, is_team_lead: e.target.checked })}
                          className="w-4 h-4 rounded border-slate-800 text-indigo-600 focus:ring-indigo-500 bg-slate-950"
                        />
                        <span>Assign as Team Lead</span>
                      </label>
                    </div>
                  </div>
                </>
              )}

              {/* STUDENT/INTERN Specific Database Schema Fields */}
              {activeTab === 'STUDENT' && (
                <>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">College / Institution *</label>
                      <input
                        type="text"
                        required
                        value={studentForm.college_institution}
                        onChange={(e) => setStudentForm({ ...studentForm, college_institution: e.target.value })}
                        placeholder="e.g. Stanford University"
                        className="w-full bg-slate-950 border border-slate-800 text-xs text-white px-3 py-2.5 rounded-xl focus:outline-none focus:ring-1 focus:ring-indigo-500"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">Degree Program</label>
                      <input
                        type="text"
                        value={studentForm.degree_program}
                        onChange={(e) => setStudentForm({ ...studentForm, degree_program: e.target.value })}
                        placeholder="e.g. BBA"
                        className="w-full bg-slate-950 border border-slate-800 text-xs text-white px-3 py-2.5 rounded-xl focus:outline-none focus:ring-1 focus:ring-indigo-500"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">Role Type</label>
                      <select
                        value={studentForm.role}
                        onChange={(e) => setStudentForm({ ...studentForm, role: e.target.value })}
                        className="w-full bg-slate-950 border border-slate-800 text-xs text-white px-3 py-2.5 rounded-xl focus:outline-none focus:ring-1 focus:ring-indigo-500"
                      >
                        <option value="intern">Intern</option>
                        <option value="student">Student</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">Current Status</label>
                      <select
                        value={studentForm.current_status}
                        onChange={(e) => setStudentForm({ ...studentForm, current_status: e.target.value })}
                        className="w-full bg-slate-950 border border-slate-800 text-xs text-white px-3 py-2.5 rounded-xl focus:outline-none focus:ring-1 focus:ring-indigo-500"
                      >
                        <option value="AVAILABLE">AVAILABLE</option>
                        <option value="ALLOCATED">ALLOCATED</option>
                        <option value="ON_LEAVE">ON_LEAVE</option>
                      </select>
                    </div>
                  </div>

                  {/* Dual Resume Option: Direct Link or Bucket Upload */}
                  <div className="space-y-2 pt-2 border-t border-slate-800/80">
                    <div className="flex items-center justify-between">
                      <label className="block text-xs font-semibold text-slate-300">Resume Source *</label>
                      <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
                        <button
                          type="button"
                          onClick={() => setResumeMode('URL')}
                          className={`flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium transition ${
                            resumeMode === 'URL' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                          }`}
                        >
                          <LinkIcon className="w-3 h-3" /> Direct URL
                        </button>
                        <button
                          type="button"
                          onClick={() => setResumeMode('FILE')}
                          className={`flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium transition ${
                            resumeMode === 'FILE' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                          }`}
                        >
                          <Upload className="w-3 h-3" /> Upload PDF
                        </button>
                      </div>
                    </div>

                    {resumeMode === 'URL' ? (
                      <input
                        type="url"
                        required={!editingId}
                        value={studentForm.resume_document_url}
                        onChange={(e) => setStudentForm({ ...studentForm, resume_document_url: e.target.value })}
                        placeholder="https://storage.bucket.com/resumes/candidate.pdf"
                        className="w-full bg-slate-950 border border-slate-800 text-xs text-white px-3 py-2.5 rounded-xl focus:outline-none focus:ring-1 focus:ring-indigo-500"
                      />
                    ) : (
                      <div className="border-2 border-dashed border-slate-800 rounded-xl p-4 text-center bg-slate-950/50 hover:border-slate-700 transition">
                        <input
                          type="file"
                          accept=".pdf,.doc,.docx"
                          onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                          className="hidden"
                          id="resume-upload"
                        />
                        <label htmlFor="resume-upload" className="cursor-pointer flex flex-col items-center gap-2">
                          <Upload className="w-6 h-6 text-indigo-400" />
                          <span className="text-xs font-medium text-slate-300">
                            {selectedFile ? selectedFile.name : 'Click to select PDF resume file'}
                          </span>
                          <span className="text-[10px] text-slate-500">Auto-uploads to DB cloud storage bucket</span>
                        </label>
                      </div>
                    )}
                  </div>
                </>
              )}

              {/* Footer Actions */}
              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs rounded-xl shadow-lg shadow-indigo-600/20 transition-all"
                >
                  <Check className="w-4 h-4" />
                  <span>{editingId ? 'Save Changes' : 'Create Record'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};