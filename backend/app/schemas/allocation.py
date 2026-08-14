# app/schemas/allocation.py
from pydantic import BaseModel, Field
from typing import Optional, Literal
from uuid import UUID
from datetime import datetime

class AllocationBase(BaseModel):
    resource_type: Literal["intern", "employee", "student"] = Field(
        ..., description="Type of resource allocated"
    )
    resource_id: UUID = Field(
        ..., description="UUID of the intern or employee being allocated"
    )
    project_id: UUID = Field(
        ..., description="UUID of the project or training initiative"
    )
    role_on_project: str = Field(
        ..., description="Role e.g. 'intern_developer', 'lead_mentor', 'trainer'"
    )
    allocated_hours: int = Field(
        ..., ge=1, description="Weekly hours dedicated to this project"
    )
    suitability_score: Optional[float] = Field(
        default=1.0, ge=0.0, le=1.0, description="AI similarity match score (0.0 to 1.0)"
    )
    status: Literal["proposed", "confirmed", "rejected", "completed"] = Field(
        default="proposed", description="Approval lifecycle state of the allocation"
    )

class AllocationCreate(AllocationBase):
    """Payload format when proposing or creating a new allocation."""
    pass

class AllocationUpdate(BaseModel):
    """Payload format when updating an allocation (e.g. approving a proposed match)."""
    role_on_project: Optional[str] = None
    allocated_hours: Optional[int] = Field(default=None, ge=1)
    suitability_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    status: Optional[Literal["proposed", "confirmed", "rejected", "completed"]] = None

class AllocationResponse(AllocationBase):
    """JSON response model returned to the API client."""
    allocation_id: UUID
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True