from pydantic import BaseModel, EmailStr
from typing import Optional, Literal
from uuid import UUID

class InternBase(BaseModel):
    name: str
    email: EmailStr
    college_institution: str
    degree_program: Optional[str] = None
    role: Literal["intern", "student"] = "intern"  # 🆕 Restricted to 'intern' or 'student'
    weekly_capacity_hours: int = 20

class InternCreate(InternBase):
    resume_document_url: str

class InternResponse(InternBase):
    intern_id: UUID
    review_status: str
    resume_document_url: str

    class Config:
        from_attributes = True