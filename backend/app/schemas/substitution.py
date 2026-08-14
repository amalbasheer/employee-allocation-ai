# app/schemas/substitution.py
from pydantic import BaseModel, Field
from typing import Optional, Literal
from uuid import UUID
from datetime import datetime

class SubstitutionBase(BaseModel):
    project_id: UUID
    original_resource_id: UUID = Field(..., description="UUID of the person being replaced")
    replacement_resource_id: Optional[UUID] = Field(None, description="UUID of the new candidate")
    reason: str = Field(..., description="Reason for replacement (e.g. 'unavailability', 'skill mismatch')")
    status: Literal["requested", "approved", "rejected", "completed"] = "requested"

class SubstitutionCreate(SubstitutionBase):
    pass

class SubstitutionUpdate(BaseModel):
    replacement_resource_id: Optional[UUID] = None
    reason: Optional[str] = None
    status: Optional[Literal["requested", "approved", "rejected", "completed"]] = None

class SubstitutionResponse(SubstitutionBase):
    substitution_id: UUID
    requested_at: Optional[datetime] = None

    class Config:
        from_attributes = True