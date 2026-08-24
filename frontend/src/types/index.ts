// ==========================================
// COMMON / ENUM TYPES
// ==========================================
export type Role = 'ADMIN' | 'SUPERADMIN' | 'EMPLOYEE' | 'STUDENT' | 'INTERN' | 'GUEST';
export type PriorityLevel = 'LOW' | 'MEDIUM' | 'HIGH';
export type ProjectStatus = 'open' | 'in_progress' | 'completed' | 'cancelled';
export type AllocationStatus = 'proposed' | 'accepted' | 'rejected' | 'assigned' | 'substituted';

export enum UserRole {
  ADMIN = 'admin',
  SUPERADMIN = 'superadmin',
  EMPLOYEE = 'employee',
  STUDENT = 'student',
  INTERN = 'intern',
}

// ==========================================
// AUTH & USER INTERFACES
// ==========================================
export interface User {
  id: string;
  email: string;
  name: string;
  role: Role;
  department?: string;
  avatarUrl?: string;
}

export interface UserProfile {
  id: string;
  email: string;
  role: UserRole | string;
  name?: string;
}

export interface LoginRequest {
  username: string; // Form-data / OAuth2 standard uses username/password
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

// ==========================================
// PROJECT & REQUIREMENT INTERFACES
// ==========================================
export interface ProjectRequirement {
  requirement_id?: string;
  project_id?: string;
  skill_id: string;
  skill_name: string;
  min_proficiency: number;
  is_mandatory: boolean;
  requirement_embedding?: number[];
}

export interface Project {
  project_id: string;
  title: string;
  description: string;
  project_type: 'batch' | 'workshop' | 'webinar' | 'seminar' | 'demo' | 'internal_project' | string;
  category?: 'training_engagement' | 'work_engagement' | string;
  required_roles?: string[];
  start_date: string;
  end_date?: string;
  required_hours_per_week: number;
  priority_level: PriorityLevel;
  status: ProjectStatus;
  created_at?: string;
  requirements?: ProjectRequirement[];
  raw_skills?: string[];
}

export interface StatusUpdateRequest {
  status: ProjectStatus | AllocationStatus;
  changed_by?: string;
  reason?: string;
}

// ==========================================
// ALLOCATION & RECOMMENDATION INTERFACES
// ==========================================
export interface Allocation {
  allocation_id: string;
  resource_type: 'MENTOR' | 'INTERN' | string;
  resource_id: string;
  project_id: string;
  role_on_project: string;
  allocated_hours: number;
  suitability_score: number;
  status: AllocationStatus;
  assigned_at?: string;
  assigned_by?: string;
}

export interface Substitution {
  substitution_id: string;
  original_allocation_id: string;
  substitute_resource_type: string;
  substitute_resource_id: string;
  reason?: string;
  created_at: string;
}

export interface AllocationLog {
  log_id: string;
  allocation_id: string;
  action: string;
  old_status?: string;
  new_status?: string;
  changed_by: string;
  reason?: string;
  timestamp: string;
}

export interface ResourceMatch {
  resource_id: string;
  resource_type: string;
  name?: string;
  suitability_score: number;
  match_reasons?: string[];
  skills?: string[];
}

export interface ProposeAllocationPayload {
  project_id: string;
  resource_type: string;
  resource_id: string;
  role_on_project: string;
  allocated_hours: number;
  suitability_score: number;
}

export interface SubstituteAllocationPayload {
  substitute_resource_type: string;
  substitute_resource_id: string;
  reason: string;
}

// ==========================================
// CHAT & AI INTERFACES
// ==========================================



export interface RecommendationItem {
  resource_id?: string;
  name: string;
  resource_type: string;
  suitability_score: number;
  reason?: string;
}

export interface ChatQueryRequest {
  query: string;
  user_id?: string | null;
}

export interface ChatQueryResponse {
  id: string;
  user_id: string;
  query: string;
  response_text: string;
  recommendations?: RecommendationItem[];
  created_at?: string;
}

// ==========================================
// SKILLS & RESOURCE POOL TYPES
// ==========================================
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