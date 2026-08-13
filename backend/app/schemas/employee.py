import uuid
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


# --- Employee Skill Schemas ---

class EmployeeSkillBase(BaseModel):
    skill_id: uuid.UUID
    proficiency_level: int = Field(default=1, ge=1, le=5, description="Proficiency level from 1 (Novice) to 5 (Expert)")


class EmployeeSkillCreate(EmployeeSkillBase):
    pass


class EmployeeSkillResponse(EmployeeSkillBase):
    skill_name: Optional[str] = None
    is_custom_override: bool = False

    class Config:
        from_attributes = True


# --- Availability Schemas ---

class AvailabilityBase(BaseModel):
    week_start_date: date
    available_hours: int = Field(default=40, ge=0, le=168)
    is_on_leave: bool = False


class AvailabilityCreate(AvailabilityBase):
    pass


class AvailabilityResponse(AvailabilityBase):
    availability_id: uuid.UUID
    resource_id: uuid.UUID
    resource_type: str
    week_start_date: date
    available_hours: int
    is_on_leave: bool

    class Config:
        from_attributes = True


# --- Employee CRUD Schemas ---

class EmployeeCreate(BaseModel):
    name: str
    email: EmailStr
    designation_id: uuid.UUID
    department: str
    experience_years: float = Field(default=0.0, ge=0.0)
    weekly_capacity_hours: int = Field(default=40, ge=0, le=168)
    skills: Optional[List[EmployeeSkillCreate]] = []


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    designation_id: Optional[uuid.UUID] = None
    department: Optional[str] = None
    experience_years: Optional[float] = Field(default=None, ge=0.0)
    weekly_capacity_hours: Optional[int] = Field(default=None, ge=0, le=168)


class EmployeeResponse(BaseModel):
    employee_id: uuid.UUID
    name: str
    email: EmailStr
    designation_id: uuid.UUID
    department: str
    experience_years: float
    weekly_capacity_hours: int
    created_at: datetime

    class Config:
        from_attributes = True


class EmployeeDetailResponse(EmployeeResponse):
    skills: List[EmployeeSkillResponse] = []
    availabilities: List[AvailabilityResponse] = []

    class Config:
        from_attributes = True