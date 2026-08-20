import uuid
import traceback
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.api.deps import get_db, get_current_user, require_admin
from app.models.allocation import Allocation, AllocationLog, Substitution
from app.models.project import Project, ProjectRequirement
from app.models.taxonomy import Skill
from app.models.employee import CompanyEmployee
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


def safe_get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def calculate_progress(status: str) -> int:
    status_lower = str(status).lower()
    if status_lower in ["completed", "done", "finished"]:
        return 100
    elif status_lower in ["in_progress", "active", "started", "assigned"]:
        return 50
    elif status_lower in ["accepted", "proposed", "pending"]:
        return 10
    return 0


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

    # Create Audit Log
    log = AllocationLog(
        allocation_id=new_allocation.allocation_id,
        action=f"PROPOSED candidate {payload.resource_id} for role '{payload.role_on_project}'",
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

    user_role = str(current_user.role).lower()
    prev_status = allocation.status
    target_status = payload.status

    # --- ACTION HANDLER: ADMIN CONFIRM (ASSIGN) ---
    if user_role in ["admin", "superadmin"]:
        if target_status == AllocationStatus.ASSIGNED:
            if prev_status != AllocationStatus.ACCEPTED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot confirm assignment. Current status is '{prev_status}', but employee must accept first."
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

    # --- ACTION HANDLER: EMPLOYEE / INTERN ACCEPT OR REJECT ---
    elif user_role in ["employee", "student", "intern"]:
        if str(allocation.resource_id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only accept or reject allocations assigned to your account."
            )

        if prev_status != AllocationStatus.PROPOSED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Allocation cannot be updated from state '{prev_status}'."
            )

        if target_status in [AllocationStatus.ACCEPTED, AllocationStatus.REJECTED]:
            allocation.status = target_status
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Employees can only transition status to 'ACCEPTED' or 'REJECTED'."
            )
    else:
        raise HTTPException(status_code=403, detail="Unauthorized role.")

    # Detail audit log text
    reason_suffix = f" | Reason: {payload.reason}" if getattr(payload, "reason", None) else ""
    log = AllocationLog(
        allocation_id=allocation.allocation_id,
        action=f"STATUS_CHANGE: {prev_status} -> {target_status}{reason_suffix}",
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
        raise HTTPException(status_code=404, detail="Original allocation record not found")

    # 1. Mark original allocation as SUBSTITUTED
    orig_allocation.status = AllocationStatus.SUBSTITUTED

    # 2. Record substitution details
    sub_record = Substitution(
        original_allocation_id=orig_allocation.allocation_id,
        substitute_resource_type=payload.substitute_resource_type,
        substitute_resource_id=payload.substitute_resource_id,
        reason=payload.reason
    )
    db.add(sub_record)

    # 3. Create replacement allocation in PROPOSED state
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

    # 4. Log changes into allocation_log
    log = AllocationLog(
        allocation_id=orig_allocation.allocation_id,
        action=f"SUBSTITUTED by {admin_user.email}. New Allocation ID: {new_allocation.allocation_id} | Reason: {payload.reason}",
        changed_by=admin_user.email
    )
    db.add(log)

    db.commit()
    db.refresh(sub_record)
    return sub_record


# -------------------------------------------------------------------
# 4. QUERY USER ALLOCATIONS ("MY ALLOCATIONS")
# -------------------------------------------------------------------
@router.get("/my-allocations")
def get_my_allocations(
    resource_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        user_ids = set()
        for field in ["id", "intern_id", "employee_id", "user_id", "student_id"]:
            val = safe_get(current_user, field)
            if val:
                user_ids.add(str(val))

        if resource_id:
            user_ids.add(str(resource_id))

        valid_ids = [uid for uid in user_ids if uid]
        if not valid_ids:
            return []

        allocations_list = db.query(Allocation).filter(
            Allocation.resource_id.in_(valid_ids)
        ).all()

        if not allocations_list:
            return []

        results = []
        for alloc in allocations_list:
            proj_id = alloc.project_id
            project_obj = db.query(Project).filter(Project.project_id == proj_id).first()
            if not project_obj:
                continue

            project_title = safe_get(project_obj, "title") or "Assigned Project"
            category = safe_get(project_obj, "project_type") or "Software Engineering"
            project_status = safe_get(project_obj, "status") or "open"
            description = safe_get(project_obj, "description") or ""
            start_date = safe_get(project_obj, "start_date")
            end_date = safe_get(project_obj, "end_date")

            suitability_score = safe_get(alloc, "suitability_score") or 0.0
            alloc_status = safe_get(alloc, "status") or "assigned"

            req_skill_ids = db.query(ProjectRequirement.skill_id).filter(
                ProjectRequirement.project_id == proj_id
            ).all()
            
            skill_ids = [s[0] for s in req_skill_ids if s[0]]
            tech_stack = []
            if skill_ids:
                skills_objs = db.query(Skill).filter(Skill.skill_id.in_(skill_ids)).all()
                tech_stack = [
                    safe_get(sk, "skill_name") or safe_get(sk, "name") or str(sk.skill_id) 
                    for sk in skills_objs
                ]

            mentor_name = "Pending Mentor Assignment"
            mentor_id = safe_get(project_obj, "mentor_id")
            
            if mentor_id:
                mentor_obj = db.query(CompanyEmployee).filter(CompanyEmployee.employee_id == mentor_id).first()
                if mentor_obj:
                    mentor_name = safe_get(mentor_obj, "first_name", "") + " " + safe_get(mentor_obj, "last_name", "")
            else:
                mentor_alloc = db.query(Allocation).filter(
                    Allocation.project_id == proj_id,
                    ~Allocation.resource_id.in_(valid_ids)
                ).first()
                if mentor_alloc and mentor_alloc.resource_id:
                    mentor_obj = db.query(CompanyEmployee).filter(CompanyEmployee.employee_id == mentor_alloc.resource_id).first()
                    if mentor_obj:
                        mentor_name = f"{safe_get(mentor_obj, 'first_name', '')} {safe_get(mentor_obj, 'last_name', '')}".strip() or "Assigned Mentor"

            results.append({
                "allocation_id": str(alloc.allocation_id),
                "project_id": proj_id,
                "title": project_title,
                "category": category,
                "role": safe_get(alloc, "role_on_project") or "Contributor",
                "mentor": mentor_name,
                "project_status": str(project_status).lower(),
                "status": str(alloc_status).lower(),
                "description": description,
                "match_score": suitability_score,
                "tech_stack": tech_stack,
                "progress_percentage": calculate_progress(alloc_status),
                "start_date": str(start_date) if start_date else "N/A",
                "due_date": str(end_date) if end_date else "N/A"
            })

        return results

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Internal Server Error during allocation lookup: {str(e)}"
        )


# -------------------------------------------------------------------
# 5. ADMIN REVIEW ENDPOINT
# -------------------------------------------------------------------
@router.patch("/{allocation_id}/admin-review", response_model=AllocationResponse)
def admin_review_allocation(
    allocation_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    admin_user: UserProfile = Depends(require_admin)
):
    alloc = db.query(Allocation).filter(Allocation.allocation_id == allocation_id).first()
    if not alloc:
        raise HTTPException(status_code=404, detail="Allocation record not found")

    action = payload.get("action")
    if action == "confirm":
        if alloc.status != AllocationStatus.ACCEPTED:
            raise HTTPException(status_code=400, detail="Cannot confirm an allocation that has not been ACCEPTED by the resource.")
        alloc.status = AllocationStatus.ASSIGNED
        
        project = db.query(Project).filter(Project.project_id == alloc.project_id).first()
        if project and project.status == ProjectStatus.OPEN:
            project.status = ProjectStatus.IN_PROGRESS

    elif action == "reject":
        alloc.status = AllocationStatus.REJECTED
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'confirm' or 'reject'.")

    log = AllocationLog(
        allocation_id=alloc.allocation_id,
        action=f"ADMIN_REVIEW action '{action}' executed by {admin_user.email}",
        changed_by=admin_user.email
    )
    db.add(log)
    db.commit()
    db.refresh(alloc)
    return alloc


@router.get("/{allocation_id}/logs", response_model=List[AllocationLogResponse])
def get_allocation_logs(
    allocation_id: str,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Fetch audit history logs for a specific allocation."""
    logs = db.query(AllocationLog).filter(
        AllocationLog.allocation_id == allocation_id
    ).order_by(AllocationLog.timestamp.desc()).all()
    
    return logs