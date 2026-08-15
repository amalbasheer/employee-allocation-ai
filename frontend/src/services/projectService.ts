import { apiClient } from './api';
import { Project } from '../types';

export const projectService = {
  getProjects: async (): Promise<Project[]> => {
    const response = await apiClient.get<Project[]>('/projects/');
    return response.data;
  },

  getProjectById: async (id: string): Promise<Project> => {
    const response = await apiClient.get<Project>(`/projects/${id}`);
    return response.data;
  },

  createProject: async (projectData: Partial<Project>): Promise<Project> => {
    const response = await apiClient.post<Project>('/projects/', projectData);
    return response.data;
  },
};