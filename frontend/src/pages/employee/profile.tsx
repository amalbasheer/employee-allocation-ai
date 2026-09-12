import React, { useState, useEffect, useCallback } from 'react';

export interface SkillCatalogItem {
  skill_id: string;
  skill_name: string;
}

export interface EmployeeSkill {
  skill_id: string;
  skill_name: string;
  proficiency_level: number;
}

interface EmployeeSkillsManagerProps {
  employeeId?: string;
}

const PROFICIENCY_LEVELS = [1, 2, 3, 4, 5];

export const EmployeeSkillsManager: React.FC<EmployeeSkillsManagerProps> = ({
  employeeId: propEmployeeId,
}) => {
  const [employeeSkills, setEmployeeSkills] = useState<EmployeeSkill[]>([]);
  const [skillCatalog, setSkillCatalog] = useState<SkillCatalogItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Form State
  const [showAddForm, setShowAddForm] = useState<boolean>(false);
  const [newSkillName, setNewSkillName] = useState<string>('');
  const [newProficiency, setNewProficiency] = useState<number>(3);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Inline Editing State
  const [editingSkillId, setEditingSkillId] = useState<string | null>(null);
  const [editProficiency, setEditProficiency] = useState<number>(3);

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

  const getAuthHeaders = useCallback((): HeadersInit => {
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

    return {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
  }, []);

  const fetchData = useCallback(async () => {
    const targetEmployeeId = getActiveEmployeeId();
    if (!targetEmployeeId) {
      setError('Employee ID could not be identified.');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const headers = getAuthHeaders();
      const [skillsRes, catalogRes] = await Promise.all([
        fetch(`${API_BASE}/api/employees/${targetEmployeeId}/skills`, { headers }),
        fetch(`${API_BASE}/api/employees/skills/catalog`, { headers }),
      ]);

      if (!skillsRes.ok) throw new Error('Failed to fetch employee skills');
      if (!catalogRes.ok) throw new Error('Failed to fetch skill catalog');

      const skillsData: EmployeeSkill[] = await skillsRes.json();
      const catalogData: SkillCatalogItem[] = await catalogRes.json();

      setEmployeeSkills(skillsData);
      setSkillCatalog(catalogData);
    } catch (err: any) {
      setError(err.message || 'An error occurred while loading data.');
    } finally {
      setLoading(false);
    }
  }, [API_BASE, getActiveEmployeeId, getAuthHeaders]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // 1. Add Skill (POST)
  const handleAddSkill = async (e: React.FormEvent) => {
    e.preventDefault();
    const targetEmployeeId = getActiveEmployeeId();
    if (!newSkillName.trim() || !targetEmployeeId) return;

    setIsSubmitting(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/api/employees/${targetEmployeeId}/skills`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          skill_name: newSkillName.trim(),
          proficiency_level: Number(newProficiency),
        }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Failed to add skill');
      }

      await fetchData();
      setNewSkillName('');
      setNewProficiency(3);
      setShowAddForm(false);
    } catch (err: any) {
      setError(err.message || 'Failed to save skill');
    } finally {
      setIsSubmitting(false);
    }
  };

  // 2. Update Proficiency (PUT)
  const handleSaveProficiency = async (skillId: string) => {
    const targetEmployeeId = getActiveEmployeeId();
    if (!targetEmployeeId) return;

    try {
      const response = await fetch(
        `${API_BASE}/api/employees/${targetEmployeeId}/skills/${skillId}`,
        {
          method: 'PUT',
          headers: getAuthHeaders(),
          body: JSON.stringify({ proficiency_level: Number(editProficiency) }),
        }
      );

      if (!response.ok) throw new Error('Failed to update proficiency');

      setEmployeeSkills((prev) =>
        prev.map((item) =>
          item.skill_id === skillId
            ? { ...item, proficiency_level: Number(editProficiency) }
            : item
        )
      );
      setEditingSkillId(null);
    } catch (err: any) {
      setError(err.message || 'Failed to update proficiency');
    }
  };

  // 3. Delete Skill (DELETE)
  const handleDeleteSkill = async (skillId: string) => {
    const targetEmployeeId = getActiveEmployeeId();
    if (!targetEmployeeId) return;

    if (!window.confirm('Are you sure you want to remove this skill?')) return;

    try {
      const response = await fetch(
        `${API_BASE}/api/employees/${targetEmployeeId}/skills/${skillId}`,
        {
          method: 'DELETE',
          headers: getAuthHeaders(),
        }
      );

      if (!response.ok) throw new Error('Failed to delete skill');

      setEmployeeSkills((prev) => prev.filter((item) => item.skill_id !== skillId));
    } catch (err: any) {
      setError(err.message || 'Failed to delete skill');
    }
  };

  const currentEmployeeId = getActiveEmployeeId();

  if (loading) {
  return <div className="p-6 text-center text-gray-500 font-medium">Loading skills catalog...</div>;
}

return (
  <div className="w-full py-4">
    {/* Header */}
    <div className="flex justify-between items-center mb-6 pb-4 border-b border-gray-200">
      <div>
        <h2 className="text-xl font-bold text-white">Skills</h2>
        <p className="text-xs text-gray-500">Employee ID: {currentEmployeeId || 'N/A'}</p>
      </div>
      <button
        onClick={() => setShowAddForm(!showAddForm)}
        className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition"
      >
        {showAddForm ? 'Cancel' : '+ Add Skill'}
      </button>
    </div>

    {error && (
      <div className="mb-4 p-3 text-sm text-red-700 bg-red-50 rounded-lg border border-red-200">
        {error}
      </div>
    )}

    {/* Add Skill Form */}
{showAddForm && (
  <form 
    onSubmit={handleAddSkill} 
    className="mb-6 p-5 bg-slate-50/80 rounded-xl border border-slate-200/80 shadow-sm transition-all"
  >
    <div className="flex items-center justify-between mb-4">
      <h3 className="text-sm font-bold text-slate-800 tracking-tight">Add New Skill</h3>
      <span className="text-xs text-slate-400 font-medium">Step 1 of 1</span>
    </div>

    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {/* Skill Name Input */}
      <div>
        <label className="block text-xs font-semibold text-slate-600 mb-1.5 uppercase tracking-wider">
          Skill Name
        </label>
        <input
          type="text"
          list="skill-catalog-list"
          placeholder="Type or select skill..."
          value={newSkillName}
          onChange={(e) => setNewSkillName(e.target.value)}
          className="w-full px-3.5 py-2.5 text-sm text-slate-800 bg-white border border-slate-300 rounded-lg shadow-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 placeholder:text-slate-400 transition"
          required
        />
        <datalist id="skill-catalog-list">
          {skillCatalog.map((cat) => (
            <option key={cat.skill_id} value={cat.skill_name} />
          ))}
        </datalist>
      </div>

      {/* Proficiency Level Select */}
      <div>
        <label className="block text-xs font-semibold text-slate-600 mb-1.5 uppercase tracking-wider">
          Proficiency Level
        </label>
        <select
          value={newProficiency}
          onChange={(e) => setNewProficiency(Number(e.target.value))}
          className="w-full px-3.5 py-2.5 text-sm font-medium text-slate-800 bg-white border border-slate-300 rounded-lg shadow-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition cursor-pointer"
        >
          {PROFICIENCY_LEVELS.map((lvl) => (
            <option key={lvl} value={lvl}>
              Level {lvl}
            </option>
          ))}
        </select>
      </div>

      {/* Save Button */}
      <div className="flex items-end">
        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full py-2.5 px-4 text-sm font-semibold text-white bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 rounded-lg shadow-sm hover:shadow transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
        >
          {isSubmitting ? 'Saving...' : 'Save Skill'}
        </button>
      </div>
    </div>
  </form>
)}



    {/* Skills Table */}
    {employeeSkills.length === 0 ? (
      <div className="text-center py-8 text-gray-400 text-sm italic">
        No skills assigned yet. Click "+ Add Skill" to start.
      </div>
    ) : (
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wider">
              
              <th className="py-3 px-4">Skills</th>
              <th className="py-3 px-4">Proficiency Level</th>
              <th className="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 text-sm">
            {employeeSkills.map((item) => (
              <tr key={item.skill_id} className="hover:bg-gray-100/50 transition-colors">
                
                <td className="py-3 px-4 font-semibold text-cyan-800">{item.skill_name}</td>
                <td className="py-3 px-4">
                  {editingSkillId === item.skill_id ? (
                    <select
                      value={editProficiency}
                      onChange={(e) => setEditProficiency(Number(e.target.value))}
                      className="px-2 py-1 border text-xs rounded bg-navyblue outline-none focus:ring-1 focus:ring-blue-500"
                    >
                      {PROFICIENCY_LEVELS.map((lvl) => (
                        <option key={lvl} value={lvl}>
                          Level {lvl}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <span className="inline-block px-3 py-1.5 text-xs font-semibold text-blue-800 bg-blue-100/70 rounded-full">
                      Level {item.proficiency_level}
                    </span>
                  )}
                </td>
                <td className="py-3 px-4 text-right">
                  <div className="inline-flex items-center justify-end space-x-2">
                    {editingSkillId === item.skill_id ? (
                      <>
                        {/* Save Icon Button */}
                        <button
                          onClick={() => handleSaveProficiency(item.skill_id)}
                          title="Save Changes"
                          className="p-1.5 text-green-600 hover:bg-green-100 rounded-lg transition"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                          </svg>
                        </button>
                        {/* Cancel Icon Button */}
                        <button
                          onClick={() => setEditingSkillId(null)}
                          title="Cancel"
                          className="p-1.5 text-gray-400 hover:bg-gray-200 rounded-lg transition"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </>
                    ) : (
                      <>
                        {/* Edit Icon Button */}
                        <button
                          onClick={() => {
                            setEditingSkillId(item.skill_id);
                            setEditProficiency(Number(item.proficiency_level));
                          }}
                          title="Edit Skill Level"
                          className="p-1.5 text-blue-600 hover:bg-blue-100 rounded-lg transition"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                          </svg>
                        </button>
                        {/* Delete Icon Button */}
                        <button
                          onClick={() => handleDeleteSkill(item.skill_id)}
                          title="Delete Skill"
                          className="p-1.5 text-red-500 hover:bg-red-100 rounded-lg transition"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )}
  </div>
);}