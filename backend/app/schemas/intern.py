from pydantic import BaseModel, EmailStr, HttpUrl
from typing import Optional
from uuid import UUID

# Option 1: Direct Resume URL (e.g. Existing Company Storage)
class InternRegisterWithUrl(BaseModel):
    name: str
    email: EmailStr
    college_institution: str
    degree_program: Optional[str] = None
    resume_document_url: str  # Direct URL string
    weekly_capacity_hours: Optional[int] = 20

# Response Model
class InternResponse(BaseModel):
    intern_id: UUID
    name: str
    email: EmailStr
    college_institution: str
    resume_document_url: str
    review_status: str

    class Config:
        from_attributes = True