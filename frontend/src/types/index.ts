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
  status: ProjectStatus;
  created_at: string;
  requirements: ProjectRequirement[];
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

// ==========================================
// ENUMS
// ==========================================
export enum ProjectStatus {
  OPEN = 'open',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  CANCELLED = 'cancelled',
}

export enum AllocationStatus {
  PROPOSED = 'proposed',
  ACCEPTED = 'accepted',
  REJECTED = 'rejected',
  ASSIGNED = 'assigned',
  SUBSTITUTED = 'substituted',
  CANCELLED = 'cancelled',
}

export enum UserRole {
  ADMIN = 'admin',
  SUPERADMIN = 'superadmin',
  EMPLOYEE = 'employee',
  STUDENT = 'student',
  INTERN = 'intern',
}

// ==========================================
// USER & ALLOCATION INTERFACES
// ==========================================
export interface UserProfile {
  id: string;
  email: string;
  role: UserRole | string;
  name?: string;
}

export interface Allocation {
  allocation_id: string;
  resource_type: string;
  resource_id: string;
  project_id: string;
  role_on_project: string;
  allocated_hours: number;
  suitability_score: number;
  status: AllocationStatus;
  assigned_at: string;
  assigned_by: string;
}

export interface ResourceMatch {
  resource_id: string;
  resource_type: string;
  name?: string;
  suitability_score: number;
  match_reasons?: string[];
  skills?: string[];
}

// ==========================================
// PAYLOAD SCHEMAS
// ==========================================
export interface ProposeAllocationPayload {
  project_id: string;
  resource_type: string;
  resource_id: string;
  role_on_project?: string;
  allocated_hours: number;
  suitability_score?: number;
}

export interface SubstituteAllocationPayload {
  substitute_resource_type: string;
  substitute_resource_id: string;
  reason: string;
}

// Common Skill Type
export interface Skill {
  skill_id?: string;
  skill_name: string;
  proficiency_level?: string;
  years_experience?: number;
}

// --- EMPLOYEE TYPES ---
export interface EmployeeSkill extends Skill {
  employee_id?: string;
}

export interface CompanyEmployeeCreate {
  first_name: string;
  last_name: string;
  email: string;
  department?: string;
  role?: string;
  skills?: Skill[];
}

export interface CompanyEmployeeUpdate {
  first_name?: string;
  last_name?: string;
  email?: string;
  department?: string;
  role?: string;
}

export interface CompanyEmployeeResponse {
  employee_id: string;
  first_name: string;
  last_name: string;
  email: string;
  department?: string;
  role?: string;
  skills: EmployeeSkill[];
  created_at?: string;
  updated_at?: string;
}

// --- INTERN TYPES ---
export interface InternSkill extends Skill {
  intern_id?: string;
}

export interface InternCreate {
  first_name: string;
  last_name: string;
  email: string;
  university?: string;
  major?: string;
  status?: 'AVAILABLE' | 'ASSIGNED';
  review_status?: string;
  skills?: Skill[];
}

export interface InternUpdate {
  first_name?: string;
  last_name?: string;
  email?: string;
  university?: string;
  major?: string;
  status?: 'AVAILABLE' | 'ASSIGNED';
  review_status?: string;
}

export interface InternResponse {
  intern_id: string;
  first_name: string;
  last_name: string;
  email: string;
  university?: string;
  major?: string;
  status: 'AVAILABLE' | 'ASSIGNED';
  review_status?: string;
  skills: InternSkill[];
  created_at?: string;
  updated_at?: string;
}