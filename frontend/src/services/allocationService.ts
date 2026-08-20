// src/services/allocationService.ts
import { apiClient } from './api';
import { 
  Allocation, 
  AllocationStatus, 
  ProposeAllocationPayload, 
  SubstituteAllocationPayload,
  Substitution,
  ResourceMatch,
  AllocationLog
} from '../types';

// Seed initial mock data for resilient offline fallback
let mockAllocations: Allocation[] = [
  {
    allocation_id: 'alloc-101',
    project_id: 'proj-001',
    resource_id: 'emp-501',
    resource_type: 'MENTOR',
    role_on_project: 'Technical Lead',
    allocated_hours: 20,
    suitability_score: 94,
    status: 'proposed',
  }
];

let mockLogs: AllocationLog[] = [];

export const allocationService = {
  // Fetch logged-in candidate's allocations
  getMyAllocations: async (): Promise<Allocation[]> => {
    try {
      const response = await apiClient.get<Allocation[]>('/allocations/my-allocations');
      return response.data;
    } catch (err) {
      console.warn('API Error: Falling back to mock allocations.', err);
      return mockAllocations;
    }
  },

  // Get AI recommendations for a project
  getRecommendations: async (projectId: string, topK: number = 3): Promise<ResourceMatch[]> => {
    try {
      const response = await apiClient.post<ResourceMatch[]>(`/allocations/recommend/${projectId}`, { top_k: topK });
      return response.data;
    } catch (err) {
      console.warn('API Error: Returning mock recommendations.', err);
      return [
        { resource_id: 'm-1', name: 'Dr. Sarah Jenkins', resource_type: 'MENTOR', suitability_score: 98, skills: ['PyTorch', 'FastAPI'] },
        { resource_id: 's-1', name: 'John Doe', resource_type: 'INTERN', suitability_score: 95, skills: ['Python', 'Git'] }
      ];
    }
  },

  // Admin: Propose candidate allocation
  proposeAllocation: async (payload: ProposeAllocationPayload): Promise<Allocation> => {
    try {
      const response = await apiClient.post<Allocation>('/allocations/propose', payload);
      return response.data;
    } catch (err) {
      console.warn('API Error: Mock proposing allocation.', err);
      const newAlloc: Allocation = {
        allocation_id: `alloc-${Date.now()}`,
        ...payload,
        status: 'proposed',
      };
      mockAllocations.push(newAlloc);
      return newAlloc;
    }
  },

  // Universal Status Update (Supports Rejection Reason)
  updateStatus: async (
    allocationId: string, 
    status: AllocationStatus, 
    changedBy: string = 'User',
    reason?: string
  ): Promise<Allocation> => {
    try {
      const response = await apiClient.patch<Allocation>(`/allocations/${allocationId}/status`, { 
        status, 
        changed_by: changedBy,
        reason 
      });
      return response.data;
    } catch (err) {
      console.warn(`API Error: Updating mock allocation status to ${status}.`, err);
      const alloc = mockAllocations.find(a => a.allocation_id === allocationId);
      if (alloc) alloc.status = status;
      return alloc || {
        allocation_id: allocationId,
        project_id: 'proj-001',
        resource_id: 'emp-501',
        resource_type: 'MENTOR',
        role_on_project: 'Lead Developer',
        allocated_hours: 20,
        suitability_score: 90,
        status,
      };
    }
  },

  // Employee/Mentor Response (Accept / Reject)
  respondToProposal: async (
    allocationId: string, 
    accept: boolean, 
    reason?: string,
    userId: string = 'Employee'
  ): Promise<Allocation> => {
    const status = accept ? ('accepted' as AllocationStatus) : ('rejected' as AllocationStatus);
    return allocationService.updateStatus(allocationId, status, userId, reason);
  },

  // Admin Final Confirmation (ACCEPTED -> ASSIGNED)
  confirmAllocation: async (allocationId: string, adminId: string = 'Admin'): Promise<Allocation> => {
    return allocationService.updateStatus(allocationId, 'assigned', adminId);
  },

  // Admin: Substitute candidate (Returns Substitution record matching Backend)
  substituteAllocation: async (
    allocationId: string, 
    payload: SubstituteAllocationPayload
  ): Promise<Substitution> => {
    try {
      const response = await apiClient.post<Substitution>(`/allocations/${allocationId}/substitute`, payload);
      return response.data;
    } catch (err) {
      console.warn('API Error: Substituting allocation in mock state.', err);
      const alloc = mockAllocations.find(a => a.allocation_id === allocationId);
      if (alloc) alloc.status = 'substituted';

      return {
        substitution_id: `sub-${Date.now()}`,
        original_allocation_id: allocationId,
        substitute_resource_type: payload.substitute_resource_type,
        substitute_resource_id: payload.substitute_resource_id,
        reason: payload.reason,
        created_at: new Date().toISOString()
      };
    }
  },

  // Fetch Audit Trail Logs for an Allocation
  getAllocationLogs: async (allocationId: string): Promise<AllocationLog[]> => {
    try {
      const response = await apiClient.get<AllocationLog[]>(`/allocations/${allocationId}/logs`);
      return response.data;
    } catch (err) {
      console.warn('API Error: Returning empty mock logs.', err);
      return mockLogs.filter(log => log.allocation_id === allocationId);
    }
  }
};