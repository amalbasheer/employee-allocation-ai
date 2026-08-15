import React from 'react';
import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';

export const UserManagement: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">User & Candidate Directory</h1>
        <p className="text-slate-400 text-sm">Manage employees, interns, designations, and vector skill profiles.</p>
      </div>

      <Card title="Registered Resources">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950 text-slate-400 uppercase font-semibold border-b border-slate-800">
              <tr>
                <th className="p-3">Name</th>
                <th className="p-3">Role</th>
                <th className="p-3">Department</th>
                <th className="p-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              <tr>
                <td className="p-3 font-medium text-white">Dr. Sarah Jenkins</td>
                <td className="p-3"><Badge label="EMPLOYEE" variant="emerald" /></td>
                <td className="p-3">AI Research</td>
                <td className="p-3 text-emerald-400 font-medium">Available</td>
              </tr>
              <tr>
                <td className="p-3 font-medium text-white">Alex Rivera</td>
                <td className="p-3"><Badge label="STUDENT" variant="amber" /></td>
                <td className="p-3">Engineering</td>
                <td className="p-3 text-amber-400 font-medium">Allocated</td>
              </tr>
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};