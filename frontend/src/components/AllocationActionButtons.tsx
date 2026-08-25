// src/components/AllocationActionButtons.tsx
import React, { useState } from 'react';
import { Allocation, AllocationStatus, UserRole } from '../types/index';
import { allocationService } from '../services/allocationService';

interface AllocationActionButtonsProps {
  allocation: Allocation;
  userRole: UserRole | string;
  onStatusUpdated?: (updatedAllocation: Allocation) => void;
  onOpenSubstituteModal?: (allocation: Allocation) => void;
}

export const AllocationActionButtons: React.FC<AllocationActionButtonsProps> = ({
  allocation,
  userRole,
  onStatusUpdated,
  onOpenSubstituteModal,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isAdmin = userRole === UserRole.ADMIN || userRole === UserRole.SUPERADMIN;

  const handleStatusChange = async (targetStatus: AllocationStatus) => {
    setLoading(true);
    setError(null);
    try {
      const updated = await allocationService.updateStatus(allocation.allocation_id, targetStatus);
      if (onStatusUpdated) onStatusUpdated(updated);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to update allocation status');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <span className="text-sm text-gray-500">Updating...</span>;
  }

  return (
    <div className="flex flex-col gap-2">
      {error && <span className="text-xs text-red-600">{error}</span>}

      <div className="flex items-center gap-2">
        {/* ========================================== */}
        {/* EMPLOYEE ACTIONS                           */}
        {/* ========================================== */}
        {!isAdmin && allocation.status === 'proposed' && (
          <>
            <button
              onClick={() => handleStatusChange('accepted')}
              className="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded text-sm font-medium transition"
            >
              Accept Proposal
            </button>
            <button
              onClick={() => handleStatusChange('rejected')}
              className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded text-sm font-medium transition"
            >
              Reject Proposal
            </button>
          </>
        )}

        {/* ========================================== */}
        {/* ADMIN ACTIONS                              */}
        {/* ========================================== */}
        {isAdmin && (
          <>
            {/* Confirm assignment when candidate accepted */}
            {allocation.status === 'accepted' && (
              <button
                onClick={() => handleStatusChange('assigned')}
                className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm font-medium transition"
              >
                Confirm Assignment
              </button>
            )}

            {/* Trigger substitution modal when candidate rejected */}
            {allocation.status === 'rejected' && onOpenSubstituteModal && (
              <button
                onClick={() => onOpenSubstituteModal(allocation)}
                className="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded text-sm font-medium transition"
              >
                Substitute Candidate
              </button>
            )}
          </>
        )}

        {/* ========================================== */}
        {/* READ-ONLY STATUS BADGES                    */}
        {/* ========================================== */}
        {allocation.status === 'assigned' && (
          <span className="px-2.5 py-1 bg-green-100 text-green-800 rounded-full text-xs font-semibold">
            Assigned (Active)
          </span>
        )}

        {allocation.status === 'substituted' && (
          <span className="px-2.5 py-1 bg-purple-100 text-purple-800 rounded-full text-xs font-semibold">
            Substituted
          </span>
        )}

        
      </div>
    </div>
  );
};