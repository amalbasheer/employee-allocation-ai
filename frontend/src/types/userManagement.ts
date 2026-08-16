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