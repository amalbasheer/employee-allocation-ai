# app/schemas/employee.py
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ==========================================
# EMPLOYEE SKILL SCHEMAS (Composite Key)
# ==========================================
class EmployeeSkillBase(BaseModel):
    skill_id: str
    proficiency_level: int = 1
   


class EmployeeSkillCreate(EmployeeSkillBase):
    employee_id: Optional[str] = None


class EmployeeSkillUpdate(BaseModel):
    proficiency_level: Optional[int] = None



class EmployeeSkillResponse(EmployeeSkillBase):
    model_config = ConfigDict(from_attributes=True)

    employee_id: str
    


# ==========================================
# AVAILABILITY SCHEMAS
# ==========================================
class AvailabilityBase(BaseModel):
    resource_type: str = "employee"  # 'employee' or 'intern'
    resource_id: str
    week_start_date: date
    available_hours: int
    is_on_leave: bool = False


class AvailabilityUpdate(BaseModel):
    available_hours: Optional[int] = None
    is_on_leave: Optional[bool] = None



class AvailabilityCreate(BaseModel):
    week_start_date: date
    available_hours: int = Field(default=40, ge=0, le=80)
    is_on_leave: bool = False


class AvailabilityResponse(BaseModel):
    availability_id: str
    resource_id: str
    resource_type: str
    week_start_date: date
    available_hours: int
    is_on_leave: bool

    class Config:
        from_attributes = True


class DateRangeLeaveRequest(BaseModel):
    start_date: date
    end_date: date
    reason: Optional[str] = None


class BatchAvailabilityUpdate(BaseModel):
    weeks: List[AvailabilityCreate]


class WeeklyBandwidthSummary(BaseModel):
    week_start_date: date
    gross_available_hours: int
    allocated_hours: int
    net_free_hours: int
    is_on_leave: bool

# ==========================================
# COMPANY EMPLOYEE SCHEMAS
# ==========================================
class CompanyEmployeeBase(BaseModel):
    name: str
    email: EmailStr
    department: str
    designation_id: Optional[str] = None
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
    designation_id: Optional[str] = None
    experience_years: Optional[float] = None
    weekly_capacity_hours: Optional[int] = None
    is_team_lead: Optional[bool] = None


class CompanyEmployeeResponse(CompanyEmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    employee_id: str
    created_at: datetime
    skills: List[EmployeeSkillResponse] = []