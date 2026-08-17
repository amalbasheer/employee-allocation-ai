// src/services/allocationService.ts
import { apiClient } from './api';
import { 
  Allocation, 
  AllocationStatus, 
  ProposeAllocationPayload, 
  SubstituteAllocationPayload,
  ResourceMatch 
} from '../types';

export const allocationService = {
  // Fetch logged-in candidate's allocations
  getMyAllocations: async (): Promise<Allocation[]> => {
    const response = await apiClient.get<Allocation[]>('/allocations/my-allocations');
    return response.data;
  },

  // Get AI recommendations for a project
  getRecommendations: async (projectId: string, topK: number = 3): Promise<ResourceMatch[]> => {
    const response = await apiClient.post<ResourceMatch[]>(`/allocations/recommend/${projectId}`, { top_k: topK });
    return response.data;
  },

  // Admin: Propose candidate allocation
  proposeAllocation: async (payload: ProposeAllocationPayload): Promise<Allocation> => {
    const response = await apiClient.post<Allocation>('/allocations/propose', payload);
    return response.data;
  },

  // Single status update method (Employee Accept/Reject, Admin Confirm/Assign)
  updateStatus: async (allocationId: string, status: AllocationStatus): Promise<Allocation> => {
    const response = await apiClient.patch<Allocation>(`/allocations/${allocationId}/status`, { status });
    return response.data;
  },

  // Convenient helper for Employee response
  respondToProposal: async (allocationId: string, accept: boolean): Promise<Allocation> => {
    const status = accept ? AllocationStatus.ACCEPTED : AllocationStatus.REJECTED;
    return allocationService.updateStatus(allocationId, status);
  },

  // Convenient helper for Admin final confirmation
  confirmAllocation: async (allocationId: string): Promise<Allocation> => {
    return allocationService.updateStatus(allocationId, AllocationStatus.ASSIGNED);
  },

  // Admin: Substitute a candidate for a rejected allocation
  substituteAllocation: async (
    allocationId: string, 
    payload: SubstituteAllocationPayload
  ): Promise<Allocation> => {
    const response = await apiClient.post<Allocation>(`/allocations/${allocationId}/substitute`, payload);
    return response.data;
  },
};