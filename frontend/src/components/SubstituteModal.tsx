// src/components/SubstituteModal.tsx
import React, { useState } from 'react';
import { Allocation, SubstituteAllocationPayload } from '../types';
import { allocationService } from '../services/allocationService';

interface SubstituteModalProps {
  allocation: Allocation | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const SubstituteModal: React.FC<SubstituteModalProps> = ({
  allocation,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [resourceType, setResourceType] = useState('employee');
  const [resourceId, setResourceId] = useState('');
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !allocation) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resourceId.trim() || !reason.trim()) {
      setError('Please fill out all required fields.');
      return;
    }

    setLoading(true);
    setError(null);

    const payload: SubstituteAllocationPayload = {
      substitute_resource_type: resourceType,
      substitute_resource_id: resourceId.trim(),
      reason: reason.trim(),
    };

    try {
      await allocationService.substituteAllocation(allocation.allocation_id, payload);
      setLoading(false);
      onSuccess();
      onClose();
    } catch (err: any) {
      setLoading(false);
      setError(err?.response?.data?.detail || 'Failed to submit substitution request.');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md p-6 border border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
          Substitute Candidate
        </h3>
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
          Replace rejected candidate for Allocation ID:{' '}
          <span className="font-mono text-gray-700 dark:text-gray-300">
            {allocation.allocation_id.slice(0, 8)}...
          </span>
        </p>

        {error && (
          <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded text-xs text-red-600 dark:text-red-400">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Substitute Resource Type
            </label>
            <select
              value={resourceType}
              onChange={(e) => setResourceType(e.target.value)}
              className="w-full px-3 py-2 border rounded-md text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="employee">Employee</option>
              <option value="intern">Intern</option>
              <option value="student">Student</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Substitute Candidate UUID
            </label>
            <input
              type="text"
              value={resourceId}
              onChange={(e) => setResourceId(e.target.value)}
              placeholder="e.g. 123e4567-e89b-12d3-a456-426614174000"
              className="w-full px-3 py-2 border rounded-md text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Reason for Substitution
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              placeholder="Provide a brief explanation for substituting this allocation..."
              className="w-full px-3 py-2 border rounded-md text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-md text-sm font-medium transition disabled:opacity-50"
            >
              {loading ? 'Submitting...' : 'Confirm Substitution'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};