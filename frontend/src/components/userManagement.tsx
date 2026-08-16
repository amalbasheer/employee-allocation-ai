import React, { useEffect, useState } from 'react';
import { employeeApi, internApi } from '../services/userService';
import {
  CompanyEmployeeResponse,
  InternResponse,
  CompanyEmployeeCreate,
  InternCreate,
} from '../types/userManagement';

export const UserManagement: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'employees' | 'interns'>('employees');
  const [employees, setEmployees] = useState<CompanyEmployeeResponse[]>([]);
  const [interns, setInterns] = useState<InternResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, [activeTab]);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      if (activeTab === 'employees') {
        const data = await employeeApi.getAll();
        setEmployees(data);
      } else {
        const data = await internApi.getAll();
        setInterns(data);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch user records');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteEmployee = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this employee?')) return;
    try {
      await employeeApi.delete(id);
      setEmployees((prev) => prev.filter((e) => e.employee_id !== id));
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to delete employee');
    }
  };

  const handleDeleteIntern = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this intern?')) return;
    try {
      await internApi.delete(id);
      setInterns((prev) => prev.filter((i) => i.intern_id !== id));
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to delete intern');
    }
  };

  const handleUpdateInternStatus = async (id: string, newStatus: 'AVAILABLE' | 'ASSIGNED') => {
    try {
      const updated = await internApi.update(id, { status: newStatus });
      setInterns((prev) => prev.map((i) => (i.intern_id === id ? updated : i)));
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to update status');
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">User Management</h1>

      {/* Tab Navigation */}
      <div className="flex border-b mb-6">
        <button
          className={`px-4 py-2 font-medium ${
            activeTab === 'employees'
              ? 'border-b-2 border-blue-600 text-blue-600'
              : 'text-gray-500'
          }`}
          onClick={() => setActiveTab('employees')}
        >
          Employees ({employees.length})
        </button>
        <button
          className={`px-4 py-2 font-medium ${
            activeTab === 'interns'
              ? 'border-b-2 border-blue-600 text-blue-600'
              : 'text-gray-500'
          }`}
          onClick={() => setActiveTab('interns')}
        >
          Interns & Students ({interns.length})
        </button>
      </div>

      {error && <div className="p-4 mb-4 bg-red-100 text-red-700 rounded">{error}</div>}
      {loading && <div className="p-4 text-gray-500">Loading records...</div>}

      {/* Employees Table */}
      {!loading && activeTab === 'employees' && (
        <table className="w-full text-left border-collapse border">
          <thead>
            <tr className="bg-gray-100 border-b">
              <th className="p-3">Name</th>
              <th className="p-3">Email</th>
              <th className="p-3">Role / Dept</th>
              <th className="p-3">Skills</th>
              <th className="p-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {employees.map((emp) => (
              <tr key={emp.employee_id} className="border-b hover:bg-gray-50">
                <td className="p-3 font-semibold">{`${emp.first_name} ${emp.last_name}`}</td>
                <td className="p-3">{emp.email}</td>
                <td className="p-3">{`${emp.role || 'N/A'} (${emp.department || 'N/A'})`}</td>
                <td className="p-3">
                  <div className="flex flex-wrap gap-1">
                    {emp.skills?.map((s, idx) => (
                      <span key={idx} className="px-2 py-0.5 text-xs bg-blue-100 text-blue-800 rounded">
                        {s.skill_name}
                      </span>
                    )) || 'None'}
                  </div>
                </td>
                <td className="p-3">
                  <button
                    onClick={() => handleDeleteEmployee(emp.employee_id)}
                    className="text-red-600 hover:underline text-sm"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Interns Table */}
      {!loading && activeTab === 'interns' && (
        <table className="w-full text-left border-collapse border">
          <thead>
            <tr className="bg-gray-100 border-b">
              <th className="p-3">Name</th>
              <th className="p-3">Email</th>
              <th className="p-3">University</th>
              <th className="p-3">Status</th>
              <th className="p-3">Skills</th>
              <th className="p-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {interns.map((intern) => (
              <tr key={intern.intern_id} className="border-b hover:bg-gray-50">
                <td className="p-3 font-semibold">{`${intern.first_name} ${intern.last_name}`}</td>
                <td className="p-3">{intern.email}</td>
                <td className="p-3">{intern.university || 'N/A'}</td>
                <td className="p-3">
                  <select
                    value={intern.status}
                    onChange={(e) =>
                      handleUpdateInternStatus(
                        intern.intern_id,
                        e.target.value as 'AVAILABLE' | 'ASSIGNED'
                      )
                    }
                    className="text-sm border rounded px-2 py-1"
                  >
                    <option value="AVAILABLE">AVAILABLE</option>
                    <option value="ASSIGNED">ASSIGNED</option>
                  </select>
                </td>
                <td className="p-3">
                  <div className="flex flex-wrap gap-1">
                    {intern.skills?.map((s, idx) => (
                      <span key={idx} className="px-2 py-0.5 text-xs bg-green-100 text-green-800 rounded">
                        {s.skill_name}
                      </span>
                    )) || 'None'}
                  </div>
                </td>
                <td className="p-3">
                  <button
                    onClick={() => handleDeleteIntern(intern.intern_id)}
                    className="text-red-600 hover:underline text-sm"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};