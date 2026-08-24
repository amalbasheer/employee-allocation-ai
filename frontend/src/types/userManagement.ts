// Common Skill Type
export interface UserSkill {
  skill_id?: string;
  skill_name: string;
  proficiency_level?: 'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED' | 'EXPERT' | string;
}

// ==========================================
// Employee Interfaces
// ==========================================

export interface CompanyEmployeeResponse {
  employee_id: string;
  first_name: string;
  last_name: string;
  email: string;
  role?: string | null;
  department?: string | null;
  availability_status?: 'AVAILABLE' | 'ALLOCATED' | 'PARTIALLY_ALLOCATED' | string;
  skills?: UserSkill[];
  created_at?: string;
  updated_at?: string;
}

export interface CompanyEmployeeCreate {
  first_name: string;
  last_name: string;
  email: string;
  role?: string;
  department?: string;
  skills?: string[] | UserSkill[];
}

export interface CompanyEmployeeUpdate {
  first_name?: string;
  last_name?: string;
  email?: string;
  role?: string;
  department?: string;
  availability_status?: string;
  skills?: string[] | UserSkill[];
}

// ==========================================
// Intern Interfaces
// ==========================================

export type InternStatus = 'AVAILABLE' | 'ASSIGNED';

export interface InternResponse {
  intern_id: string;
  first_name: string;
  last_name: string;
  email: string;
  university?: string | null;
  status: InternStatus;
  skills?: UserSkill[];
  created_at?: string;
  updated_at?: string;
}

export interface InternCreate {
  first_name: string;
  last_name: string;
  email: string;
  university?: string;
  status?: InternStatus;
  skills?: string[] | UserSkill[];
}

export interface InternUpdate {
  first_name?: string;
  last_name?: string;
  email?: string;
  university?: string;
  status?: InternStatus;
  skills?: string[] | UserSkill[];
}