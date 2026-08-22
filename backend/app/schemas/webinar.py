# backend/app/schemas/webinar.py

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


# -------------------------------------------------------------------
# Training Requirements Schemas
# -------------------------------------------------------------------

class TrainingRequirementBase(BaseModel):
    skill_id: str
    min_proficiency: int = Field(default=1, ge=1, le=5)
    is_mandatory: bool = True


class TrainingRequirementCreate(TrainingRequirementBase):
    pass


class TrainingRequirementResponse(TrainingRequirementBase):
    requirement_id: str
    engagement_id: str

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------------
# Training Engagements (Webinar, Demo, Workshop, Seminar) Schemas
# -------------------------------------------------------------------

class TrainingEngagementBase(BaseModel):
    title: str = Field(..., max_length=150)
    engagement_type: str = Field(..., description="'webinar' | 'demo' | 'workshop' | 'seminar'")
    description: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None
    required_hours: int = 2
    mentor_id: Optional[str] = None
    status: str = "open"


class TrainingEngagementCreate(TrainingEngagementBase):
    requirements: Optional[List[TrainingRequirementCreate]] = []


class TrainingEngagementUpdate(BaseModel):
    title: Optional[str] = None
    engagement_type: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    required_hours: Optional[int] = None
    mentor_id: Optional[str] = None
    status: Optional[str] = None


class TrainingEngagementResponse(TrainingEngagementBase):
    engagement_id: str
    created_at: datetime
    requirements: List[TrainingRequirementResponse] = []

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------------
# Student Batches Schemas
# -------------------------------------------------------------------

class StudentBatchBase(BaseModel):
    batch_name: str = Field(..., max_length=100)
    domain: str = Field(..., description="'Data Analytics' | 'Data Science' etc.")
    start_date: date
    end_date: date
    mentor_id: Optional[str] = None
    status: str = "open"


class StudentBatchCreate(StudentBatchBase):
    pass


class StudentBatchUpdate(BaseModel):
    batch_name: Optional[str] = None
    domain: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    mentor_id: Optional[str] = None
    status: Optional[str] = None


class StudentBatchResponse(StudentBatchBase):
    batch_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)