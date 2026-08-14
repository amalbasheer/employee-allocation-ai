from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID

class EmployeeBase(BaseModel):
    name: str
    email: EmailStr
    department: str
    experience_years: float = 0.0
    weekly_capacity_hours: int = 40
    designation_id: Optional[UUID] = None
    is_team_lead: bool = False  # 🆕 Default to False

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeResponse(EmployeeBase):
    employee_id: UUID

    class Config:
        from_attributes = True