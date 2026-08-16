# app/schemas/employee.py
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr


# ==========================================
# EMPLOYEE SKILL SCHEMAS (Composite Key)
# ==========================================
class EmployeeSkillBase(BaseModel):
    skill_id: UUID
    proficiency_level: int = 1
   


class EmployeeSkillCreate(EmployeeSkillBase):
    employee_id: Optional[UUID] = None


class EmployeeSkillUpdate(BaseModel):
    proficiency_level: Optional[int] = None



class EmployeeSkillResponse(EmployeeSkillBase):
    model_config = ConfigDict(from_attributes=True)

    employee_id: UUID
    


# ==========================================
# AVAILABILITY SCHEMAS
# ==========================================
class AvailabilityBase(BaseModel):
    resource_type: str = "employee"  # 'employee' or 'intern'
    resource_id: UUID
    week_start_date: date
    available_hours: int
    is_on_leave: bool = False


class AvailabilityCreate(AvailabilityBase):
    pass


class AvailabilityUpdate(BaseModel):
    available_hours: Optional[int] = None
    is_on_leave: Optional[bool] = None


class AvailabilityResponse(AvailabilityBase):
    model_config = ConfigDict(from_attributes=True)

    availability_id: UUID


# ==========================================
# COMPANY EMPLOYEE SCHEMAS
# ==========================================
class CompanyEmployeeBase(BaseModel):
    name: str
    email: EmailStr
    department: str
    designation_id: Optional[UUID] = None
    experience_years: float = 0.0
    weekly_capacity_hours: int = 40
    is_team_lead: bool = False


class CompanyEmployeeCreate(CompanyEmployeeBase):
    # Allows attaching initial skills during employee creation
    skills: Optional[List[EmployeeSkillBase]] = None


class CompanyEmployeeUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    department: Optional[str] = None
    designation_id: Optional[UUID] = None
    experience_years: Optional[float] = None
    weekly_capacity_hours: Optional[int] = None
    is_team_lead: Optional[bool] = None


class CompanyEmployeeResponse(CompanyEmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    employee_id: UUID
    created_at: datetime
    skills: List[EmployeeSkillResponse] = []