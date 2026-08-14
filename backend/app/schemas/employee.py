# app/schemas/employee.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID

class EmployeeBase(BaseModel):
    name: str
    email: EmailStr
    designation_id: Optional[UUID] = None
    department: str
    experience_years: float = 0.0
    weekly_capacity_hours: int = 40
    is_team_lead: bool = False

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    designation_id: Optional[UUID] = None
    department: Optional[str] = None
    experience_years: Optional[float] = None
    weekly_capacity_hours: Optional[int] = None
    is_team_lead: Optional[bool] = None

class EmployeeResponse(EmployeeBase):
    employee_id: UUID

    class Config:
        from_attributes = True

class EmployeeSkillBase(BaseModel):
    skill_id: UUID
    proficiency_level: float = 1.0
    years_experience: float = 0.0

class EmployeeSkillCreate(EmployeeSkillBase):
    pass

class EmployeeSkillResponse(EmployeeSkillBase):
    id: UUID
    employee_id: UUID

    class Config:
        from_attributes = True

class AvailabilityBase(BaseModel):
    resource_id: UUID
    resource_type: str
    allocated_hours: int = 0
    available_hours: int = 40

class AvailabilityResponse(AvailabilityBase):
    availability_id: UUID

    class Config:
        from_attributes = True