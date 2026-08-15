// src/types/index.ts

export type Role = 'ADMIN' | 'EMPLOYEE' | 'STUDENT' | 'INTERN' | 'GUEST';

export interface User {
  id: string;
  email: string;
  name: string;
  role: Role;
  department?: string;
  avatarUrl?: string;
}

export interface Skill {
  skill_id?: string;
  name: string;
  category: 'tech_stack' | 'domain' | 'soft_skill';
  confidence?: 'high' | 'medium' | 'low';
  proficiency_level?: number;
}

export interface ProjectRequirement {
  skill_id: string;
  skill_name: string;
  min_proficiency: number;
  is_mandatory: boolean;
}

export interface Project {
  project_id: string;
  title: string;
  description: string;
  project_type: 'batch' | 'workshop' | 'webinar' | 'seminar' | 'demo' | 'internal_project';
  category: 'training_engagement' | 'work_engagement';
  required_roles: string[];
  status: 'draft' | 'OPEN' | 'allocated' | 'completed';
  created_at: string;
  requirements: ProjectRequirement[];
}

export interface ResourceMatch {
  resource_id: string;
  resource_type: 'EMPLOYEE' | 'INTERN' | 'STUDENT';
  name: string;
  department_or_domain?: string;
  suitability_score: number; // 0.0 to 100.0
  matched_skills: string[];
  missing_skills: string[];
  reasoning?: string;
  ranking_position?: number; // 1, 2, or 3
}

export interface Allocation {
  allocation_id: string;
  project_id: string;
  project_title?: string;
  resource_type: 'EMPLOYEE' | 'INTERN';
  resource_id: string;
  resource_name?: string;
  role_on_project: 'mentor' | 'team_lead' | 'intern';
  suitability_score: number;
  status: 'proposed' | 'accepted_by_employee' | 'rejected_by_employee' | 'approved_by_admin' | 'substituted';
  assigned_at: string;
}

export interface ChatQueryRequest {
  query: string;
  project_id?: string;
  top_k?: number;
  filters?: Record<string, any>;
}

export interface ChatQueryResponse {
  query: string;
  response_text: string;
  recommendations: ResourceMatch[];
  metadata?: Record<string, any>;
}