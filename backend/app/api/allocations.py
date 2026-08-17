# app/api/allocations.py
import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_admin
from app.models.allocation import Allocation, AllocationLog, Substitution
from app.models.project import Project
from app.models.enums import AllocationStatus, ProjectStatus
from app.schemas.project import UserProfile
from app.schemas.allocation import (
    ProposeAllocationRequest,
    AllocationStatusUpdateRequest,
    SubstituteRequest,
    AllocationResponse,
    SubstitutionResponse,
    AllocationLogResponse,
)

router = APIRouter()

# -------------------------------------------------------------------
# 1. ADMIN PROPOSES AN ALLOCATION
# -------------------------------------------------------------------
@router.post("/propose", response_model=AllocationResponse, status_code=status.HTTP_201_CREATED)
def propose_allocation(
    payload: ProposeAllocationRequest,
    db: Session = Depends(get_db),
    admin_user: UserProfile = Depends(require_admin)
):
    project = db.query(Project).filter(Project.project_id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    new_allocation = Allocation(
        project_id=payload.project_id,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        role_on_project=payload.role_on_project,
        allocated_hours=payload.allocated_hours,
        suitability_score=payload.suitability_score,
        status=AllocationStatus.PROPOSED,
        assigned_by=admin_user.email
    )
    db.add(new_allocation)
    db.flush()

    # Log action
    log = AllocationLog(
        allocation_id=new_allocation.allocation_id,
        action=f"PROPOSED by {admin_user.email}",
        changed_by=admin_user.email
    )
    db.add(log)
    db.commit()
    db.refresh(new_allocation)
    return new_allocation


# -------------------------------------------------------------------
# 2. STATUS TRANSITION (ACCEPT / REJECT / ASSIGN)
# -------------------------------------------------------------------
@router.patch("/{allocation_id}/status", response_model=AllocationResponse)
def update_allocation_status(
    allocation_id: str,
    payload: AllocationStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    allocation = db.query(Allocation).filter(Allocation.allocation_id == allocation_id).first()
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")

    user_role = current_user.role.lower()
    prev_status = allocation.status
    target_status = payload.status

    # --- ACTION HANDLER: ADMIN CONFIRM (ASSIGN) ---
    if user_role in ["admin", "superadmin"]:
        if target_status == AllocationStatus.ASSIGNED:
            if prev_status != AllocationStatus.ACCEPTED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot confirm assignment. Current status is '{prev_status}', but employee must 'ACCEPTED' first."
                )
            allocation.status = AllocationStatus.ASSIGNED
            
            # Automatically update main project status to IN_PROGRESS
            project = db.query(Project).filter(Project.project_id == allocation.project_id).first()
            if project and project.status == ProjectStatus.OPEN:
                project.status = ProjectStatus.IN_PROGRESS

        elif target_status in [AllocationStatus.CANCELLED, AllocationStatus.PROPOSED]:
            allocation.status = target_status
        else:
            raise HTTPException(status_code=400, detail=f"Invalid target status '{target_status}' for Admin action.")

    # --- ACTION HANDLER: EMPLOYEE ACCEPT / REJECT ---
    elif user_role in ["employee", "student", "intern"]:
        if str(allocation.resource_id) != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only accept/reject allocations assigned to your account."
            )

        if prev_status != AllocationStatus.PROPOSED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Allocation cannot be updated from status '{prev_status}'."
            )

        if target_status in [AllocationStatus.ACCEPTED, AllocationStatus.REJECTED]:
            allocation.status = target_status
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Employees can only change status to 'ACCEPTED' or 'REJECTED'."
            )
    else:
        raise HTTPException(status_code=403, detail="Unauthorized role.")

    # Create Audit Log
    log = AllocationLog(
        allocation_id=allocation.allocation_id,
        action=f"STATUS_CHANGE: {prev_status} -> {target_status}",
        changed_by=current_user.email
    )
    db.add(log)
    db.commit()
    db.refresh(allocation)
    return allocation


# -------------------------------------------------------------------
# 3. SUBSTITUTE REJECTED ALLOCATION (ADMIN)
# -------------------------------------------------------------------
@router.post("/{allocation_id}/substitute", response_model=SubstitutionResponse, status_code=status.HTTP_201_CREATED)
def substitute_allocation(
    allocation_id: str,
    payload: SubstituteRequest,
    db: Session = Depends(get_db),
    admin_user: UserProfile = Depends(require_admin)
):
    orig_allocation = db.query(Allocation).filter(Allocation.allocation_id == allocation_id).first()
    if not orig_allocation:
        raise HTTPException(status_code=404, detail="Original allocation not found")

    # Mark original allocation as SUBSTITUTED
    orig_allocation.status = AllocationStatus.SUBSTITUTED

    # Create Substitution entry
    sub_record = Substitution(
        original_allocation_id=orig_allocation.allocation_id,
        substitute_resource_type=payload.substitute_resource_type,
        substitute_resource_id=payload.substitute_resource_id,
        reason=payload.reason
    )
    db.add(sub_record)

    # Create replacement allocation in PROPOSED state
    new_allocation = Allocation(
        project_id=orig_allocation.project_id,
        resource_type=payload.substitute_resource_type,
        resource_id=payload.substitute_resource_id,
        role_on_project=orig_allocation.role_on_project,
        allocated_hours=orig_allocation.allocated_hours,
        suitability_score=orig_allocation.suitability_score,
        status=AllocationStatus.PROPOSED,
        assigned_by=admin_user.email
    )
    db.add(new_allocation)
    db.flush()

    # Log changes
    log = AllocationLog(
        allocation_id=orig_allocation.allocation_id,
        action=f"SUBSTITUTED by {admin_user.email}. Replacement allocation ID: {new_allocation.allocation_id}",
        changed_by=admin_user.email
    )
    db.add(log)

    db.commit()
    db.refresh(sub_record)
    return sub_record


# -------------------------------------------------------------------
# 4. QUERY USER ALLOCATIONS ("MY PROPOSALS / MY ALLOCATIONS")
# -------------------------------------------------------------------
@router.get("/my-allocations", response_model=List[AllocationResponse])
def get_my_allocations(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    user_uuid = str(current_user.id)
    allocations = db.query(Allocation).filter(Allocation.resource_id == user_uuid).all()
    return allocations