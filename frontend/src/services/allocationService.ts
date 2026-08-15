import { apiClient } from './api';
import { Allocation, ResourceMatch } from '../types';

export const allocationService = {
  // Get recommendations for a project
  getRecommendations: async (projectId: string, topK: number = 3): Promise<ResourceMatch[]> => {
    const response = await apiClient.post<ResourceMatch[]>(`/allocations/recommend/${projectId}`, { top_k: topK });
    return response.data;
  },

  // Propose an allocation to candidate
  proposeAllocation: async (projectId: string, resourceId: string, roleOnProject: string) => {
    const response = await apiClient.post<Allocation>('/allocations/propose', {
      project_id: projectId,
      resource_id: resourceId,
      role_on_project: roleOnProject,
    });
    return response.data;
  },

  // Employee accept/reject response
  respondToProposal: async (allocationId: string, accept: boolean, reason?: string) => {
    const response = await apiClient.post<Allocation>(`/allocations/${allocationId}/respond`, {
      accept,
      rejection_reason: reason,
    });
    return response.data;
  },

  // Admin approval & trigger cascading rollover if rejected
  approveAllocation: async (allocationId: string) => {
    const response = await apiClient.post<Allocation>(`/allocations/${allocationId}/approve`);
    return response.data;
  },
};