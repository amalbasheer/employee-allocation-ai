import { apiClient } from './api';
import { Project, ProjectRequirement, StatusUpdateRequest } from '../types';

// Mock Data Fallback
let mockProjects: Project[] = [
  {
    project_id: 'p-101',
    title: 'AI Recommendation Engine',
    project_type: 'Machine Learning',
    description: 'Vector search allocation service',
    start_date: '2026-09-01',
    required_hours_per_week: 20,
    priority_level: 'HIGH',
    status: 'in_progress',
    requirements: [
      {
        requirement_id: 'req-1',
        project_id: 'p-101',
        skill_id: 'sk-python',
        skill_name: 'Python',
        min_proficiency: 4,
        is_mandatory: true,
      },
    ],
  },
];

export const projectService = {
  // 1. Fetch All Projects
  getProjects: async (): Promise<Project[]> => {
    try {
      const response = await apiClient.get<Project[]>('/projects');
      return response.data;
    } catch (err) {
      console.warn('API Error: Falling back to mock projects.', err);
      return mockProjects;
    }
  },

  // 2. Fetch Single Project with Requirements
  getProjectById: async (id: string): Promise<Project> => {
    try {
      const response = await apiClient.get<Project>(`/projects/${id}`);
      return response.data;
    } catch (err) {
      console.warn('API Error: Falling back to mock project by ID.', err);
      return mockProjects.find((p) => p.project_id === id) || mockProjects[0];
    }
  },

  // 3. Create Project (Triggers AI Skill Extraction on Backend)
  createProject: async (
    projectData: Partial<Project> & { raw_skills?: string[] }
  ): Promise<Project> => {
    try {
      const response = await apiClient.post<Project>('/projects', projectData);
      return response.data;
    } catch (err) {
      console.warn('API Error: Creating project in local mock state.', err);
      const newProjectId = `p-${Date.now()}`;

      // Mock AI skill extraction fallback
      const mockReqs: ProjectRequirement[] = (projectData.raw_skills || ['General']).map((skill, index) => ({
        requirement_id: `req-${Date.now()}-${index}`,
        project_id: newProjectId,
        skill_id: `sk-${skill.toLowerCase()}`,
        skill_name: skill,
        min_proficiency: 3,
        is_mandatory: index === 0,
      }));

      const newProject: Project = {
        project_id: newProjectId,
        title: projectData.title || 'Untitled Project',
        project_type: projectData.project_type || 'General',
        description: projectData.description || '',
        start_date: projectData.start_date || new Date().toISOString().split('T')[0],
        required_hours_per_week: projectData.required_hours_per_week || 20,
        priority_level: projectData.priority_level || 'MEDIUM',
        status: 'open',
        requirements: mockReqs,
      };

      mockProjects.unshift(newProject);
      return newProject;
    }
  },

  // 4. Update Project Details
  updateProject: async (id: string, updates: Partial<Project>): Promise<Project> => {
    try {
      const response = await apiClient.patch<Project>(`/projects/${id}`, updates);
      return response.data;
    } catch (err) {
      console.warn('API Error: Updating project in mock state.', err);
      const projIndex = mockProjects.findIndex((p) => p.project_id === id);
      if (projIndex !== -1) {
        mockProjects[projIndex] = { ...mockProjects[projIndex], ...updates };
        return mockProjects[projIndex];
      }
      throw err;
    }
  },

  // 5. Update Project Lifecycle Status
  updateProjectStatus: async (id: string, status: 'open' | 'in_progress' | 'completed' | 'cancelled'): Promise<Project> => {
    try {
      const response = await apiClient.patch<Project>(`/projects/${id}/status`, { status });
      return response.data;
    } catch (err) {
      console.warn('API Error: Updating project status in mock state.', err);
      const projIndex = mockProjects.findIndex((p) => p.project_id === id);
      if (projIndex !== -1) {
        mockProjects[projIndex].status = status;
        return mockProjects[projIndex];
      }
      throw err;
    }
  },

  // 6. Delete Project
  deleteProject: async (id: string): Promise<void> => {
    try {
      await apiClient.delete(`/projects/${id}`);
    } catch (err) {
      console.warn('API Error: Deleting project from mock state.', err);
      mockProjects = mockProjects.filter((p) => p.project_id !== id);
    }
  },

  // 7. Add Single Requirement to Existing Project
  addRequirement: async (projectId: string, requirement: Partial<ProjectRequirement>): Promise<ProjectRequirement> => {
    try {
      const response = await apiClient.post<ProjectRequirement>(`/projects/${projectId}/requirements`, requirement);
      return response.data;
    } catch (err) {
      console.warn('API Error: Adding requirement to mock state.', err);
      const newReq: ProjectRequirement = {
        requirement_id: `req-${Date.now()}`,
        project_id: projectId,
        skill_id: requirement.skill_id || 'sk-gen',
        skill_name: requirement.skill_name || 'General',
        min_proficiency: requirement.min_proficiency || 3,
        is_mandatory: requirement.is_mandatory ?? true,
      };
      const proj = mockProjects.find((p) => p.project_id === projectId);
      if (proj) {
        proj.requirements = [...(proj.requirements || []), newReq];
      }
      return newReq;
    }
  },

  // 8. Remove Requirement from Project
  removeRequirement: async (projectId: string, requirementId: string): Promise<void> => {
    try {
      await apiClient.delete(`/projects/${projectId}/requirements/${requirementId}`);
    } catch (err) {
      console.warn('API Error: Removing requirement from mock state.', err);
      const proj = mockProjects.find((p) => p.project_id === projectId);
      if (proj && proj.requirements) {
        proj.requirements = proj.requirements.filter((r) => r.requirement_id !== requirementId);
      }
    }
  },
};