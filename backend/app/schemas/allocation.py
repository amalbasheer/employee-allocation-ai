# app/schemas/allocation.py
import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.models.enums import AllocationStatus

class ProposeAllocationRequest(BaseModel):
    project_id: str
    resource_type: str  # "employee" or "student"
    resource_id: str
    role_on_project: str = "lead_mentor"
    allocated_hours: int
    suitability_score: float = 1.0

class AllocationStatusUpdateRequest(BaseModel):
    status: AllocationStatus

class SubstituteRequest(BaseModel):
    substitute_resource_type: str
    substitute_resource_id: str
    reason: str

class AllocationLogResponse(BaseModel):
    log_id: str
    allocation_id: str
    action: str
    changed_by: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

class SubstitutionResponse(BaseModel):
    substitution_id: str
    original_allocation_id: str
    substitute_resource_type: str
    substitute_resource_id: str
    reason: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AllocationResponse(BaseModel):
    allocation_id: str
    resource_type: str
    resource_id: str
    project_id: str
    role_on_project: str
    allocated_hours: int
    suitability_score: float
    status: AllocationStatus
    assigned_at: datetime
    assigned_by: str

    model_config = ConfigDict(from_attributes=True)