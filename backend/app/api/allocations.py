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
from app.models.webinar import TrainingEngagement, StudentBatch
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

def get_allocation_target(db: Session, reference_id: str, reference_type: str):
    """
    Validates and fetches the target object (Project, StudentBatch, or TrainingEngagement)
    based on the reference_type and reference_id.
    """
    ref_type = reference_type.lower().strip()

    if ref_type == "project":
        return db.query(Project).filter(Project.project_id == reference_id).first(), "Project"
    elif ref_type in ["batch", "student_batch"]:
        return db.query(StudentBatch).filter(StudentBatch.batch_id == reference_id).first(), "Student Batch"
    elif ref_type in ["training", "webinar", "engagement"]:
        return db.query(TrainingEngagement).filter(TrainingEngagement.engagement_id == reference_id).first(), "Training Engagement"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid reference_type '{reference_type}'. Must be 'project', 'batch', or 'training'."
        )


# -------------------------------------------------------------------
# 1. ADMIN PROPOSES AN ALLOCATION
# -------------------------------------------------------------------
@router.post("/propose", response_model=AllocationResponse, status_code=status.HTTP_201_CREATED)
def propose_allocation(
    payload: ProposeAllocationRequest,
    db: Session = Depends(get_db),
    admin_user: UserProfile = Depends(require_admin)
):
    # 1. Verify that the target project/batch/training engagement exists
    target_obj, target_type_label = get_allocation_target(
        db, payload.reference_id, payload.reference_type
    )

    if not target_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{target_type_label} with ID '{payload.reference_id}' not found."
        )

    # 2. Create the Allocation record
    new_allocation = Allocation(
        reference_id=payload.reference_id,
        reference_type=payload.reference_type.lower().strip(),
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        role_on_project=payload.role_on_project,
        allocated_hours=payload.allocated_hours,
        suitability_score=payload.suitability_score,
        status="proposed",
        assigned_by=admin_user.name
    )
    db.add(new_allocation)
    db.flush()  # Populates new_allocation.allocation_id for the audit log

    # 3. Create Audit Log entry
    log = AllocationLog(
        allocation_id=new_allocation.allocation_id,
        action=f"PROPOSED candidate {payload.resource_id} for role '{payload.role_on_project}' on {target_type_label} ({payload.reference_id})",
        changed_by=admin_user.name
    )
    db.add(log)

    # 4. Commit transaction
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
    
    # Identify reference and resource parameters
    ref_type = str(getattr(allocation, "reference_type", "project") or "project").lower().strip()
    ref_id = getattr(allocation, "reference_id", None) or getattr(allocation, "project_id", None)
    resource_type = str(getattr(allocation, "resource_type", "employee")).lower().strip()

    # --- ACTION HANDLER: ADMIN CONFIRM OR DIRECT ASSIGN ---
    if user_role in ["admin", "superadmin"]:
        if target_status == "assigned":
            # Employees/Mentors MUST accept first before becoming assigned
            if resource_type in ["employee", "mentor"] and prev_status != "accepted":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot confirm assignment for employee. Current status is '{prev_status}', but employee must accept first."
                )
            
            # Transition allocation status to assigned
            allocation.status = "assigned"
            
            # --- DYNAMIC TARGET ENTITY UPDATES ---
            if ref_type == "project":
                project = db.query(Project).filter(Project.project_id == ref_id).first()
                if project and getattr(project, "status", None) in ["open", "created"]:
                    project.status = "in_progress"

            elif ref_type in ["batch", "student_batch", "studentbatch"]:
                batch_obj = db.query(StudentBatch).filter(StudentBatch.batch_id == ref_id).first()
                if batch_obj:
                    # If this allocation is for an employee/mentor, set them as the batch mentor
                    if resource_type in ["employee", "mentor"]:
                        batch_obj.mentor_id = str(allocation.resource_id)
                    # If current resource is student/intern, ensure mentor_id is linked if an assigned mentor allocation exists
                    elif not getattr(batch_obj, "mentor_id", None):
                        mentor_alloc = db.query(Allocation).filter(
                            Allocation.reference_id == ref_id,
                            Allocation.resource_type.in_(["employee", "mentor"]),
                            Allocation.status.in_(["assigned", "accepted"])
                        ).first()
                        if mentor_alloc and mentor_alloc.resource_id:
                            batch_obj.mentor_id = str(mentor_alloc.resource_id)

            elif ref_type in ["training", "webinar", "engagement"]:
                training_obj = db.query(TrainingEngagement).filter(TrainingEngagement.engagement_id == ref_id).first()
                if training_obj and getattr(training_obj, "status", None) in ["scheduled", "open", "created"]:
                    training_obj.status = "in_progress"

        elif target_status in ["cancelled", "proposed"]:
            allocation.status = target_status
        else:
            raise HTTPException(status_code=400, detail=f"Invalid target status '{target_status}' for Admin action.")

    # --- ACTION HANDLER: EMPLOYEE ACCEPT OR REJECT ---
    elif user_role in ["employee", "mentor"]:
        if str(allocation.resource_id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only accept or reject allocations assigned to your account."
            )

        if prev_status != "proposed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Allocation cannot be updated from state '{prev_status}'."
            )

        if target_status in ["accepted", "rejected"]:
            allocation.status = target_status
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Employees can only transition status to 'accepted' or 'rejected'."
            )
            
    # --- ACTION HANDLER: STUDENTS/INTERNS ---
    elif user_role in ["student", "intern"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Students/interns do not update allocation status; assignments are managed directly by Admins."
        )
    else:
        raise HTTPException(status_code=403, detail="Unauthorized role.")

    # Audit logging
    reason_suffix = f" | Reason: {payload.reason}" if getattr(payload, "reason", None) else ""
    log = AllocationLog(
        allocation_id=allocation.allocation_id,
        action=f"STATUS_CHANGE: {prev_status} -> {target_status}{reason_suffix}",
        changed_by=getattr(current_user, "name", "System User")
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
    orig_allocation.status = "substituted"

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
        status="substituted",
        assigned_by=admin_user.name
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
            ref_type = (safe_get(alloc, "reference_type") or "project").lower().strip()
            ref_id = safe_get(alloc, "reference_id") or safe_get(alloc, "project_id")

            if not ref_id:
                continue

            # Initialize default fields
            title = "Assigned Engagement"
            category = "General"
            target_status = "open"
            description = ""
            start_date = None
            end_date = None
            tech_stack = []
            mentor_name = "Pending Mentor Assignment"

            # -------------------------------------------------------
            # 1. PROJECT REFERENCE
            # -------------------------------------------------------
            if ref_type == "project":
                project_obj = db.query(Project).filter(Project.project_id == ref_id).first()
                if not project_obj:
                    continue

                title = safe_get(project_obj, "title") or "Assigned Project"
                category = safe_get(project_obj, "project_type") or "Software Engineering"
                target_status = safe_get(project_obj, "status") or "open"
                description = safe_get(project_obj, "description") or ""
                start_date = safe_get(project_obj, "start_date")
                end_date = safe_get(project_obj, "end_date")

                # Retrieve project skills / tech stack
                req_skill_ids = db.query(ProjectRequirement.skill_id).filter(
                    ProjectRequirement.project_id == ref_id
                ).all()
                skill_ids = [s[0] for s in req_skill_ids if s[0]]
                if skill_ids:
                    skills_objs = db.query(Skill).filter(Skill.skill_id.in_(skill_ids)).all()
                    tech_stack = [
                        safe_get(sk, "skill_name") or safe_get(sk, "name") or str(sk.skill_id)
                        for sk in skills_objs
                    ]

                # Resolve Mentor
                mentor_id = safe_get(project_obj, "mentor_id")
                if mentor_id:
                    mentor_obj = db.query(CompanyEmployee).filter(CompanyEmployee.employee_id == mentor_id).first()
                    if mentor_obj:
                        mentor_name = f"{safe_get(mentor_obj, 'first_name', '')} {safe_get(mentor_obj, 'last_name', '')}".strip()
                else:
                    mentor_alloc = db.query(Allocation).filter(
                        Allocation.reference_id == ref_id,
                        Allocation.reference_type == "project",
                        ~Allocation.resource_id.in_(valid_ids)
                    ).first()
                    if mentor_alloc and mentor_alloc.resource_id:
                        mentor_obj = db.query(CompanyEmployee).filter(CompanyEmployee.employee_id == mentor_alloc.resource_id).first()
                        if mentor_obj:
                            mentor_name = f"{safe_get(mentor_obj, 'first_name', '')} {safe_get(mentor_obj, 'last_name', '')}".strip() or "Assigned Mentor"

            # -------------------------------------------------------
            # 2. BATCH REFERENCE
            # -------------------------------------------------------
            elif ref_type in ["batch", "student_batch"]:
                batch_obj = db.query(StudentBatch).filter(StudentBatch.batch_id == ref_id).first()
                if not batch_obj:
                    continue

                title = safe_get(batch_obj, "batch_name") or safe_get(batch_obj, "name") or "Student Batch"
                category = safe_get(batch_obj, "program") or "Student Batch"
                target_status = safe_get(batch_obj, "status") or "active"
                description = safe_get(batch_obj, "description") or ""
                start_date = safe_get(batch_obj, "start_date")
                end_date = safe_get(batch_obj, "end_date")
                mentor_name = safe_get(batch_obj, "instructor_name") or safe_get(batch_obj, "trainer_name") or "Batch Instructor"

            # -------------------------------------------------------
            # 3. TRAINING / WEBINAR REFERENCE
            # -------------------------------------------------------
            elif ref_type in ["training", "webinar", "engagement"]:
                training_obj = db.query(TrainingEngagement).filter(TrainingEngagement.engagement_id == ref_id).first()
                if not training_obj:
                    continue

                title = safe_get(training_obj, "title") or safe_get(training_obj, "engagement_name") or "Training Engagement"
                category = safe_get(training_obj, "type") or safe_get(training_obj, "category") or "Training"
                target_status = safe_get(training_obj, "status") or "scheduled"
                description = safe_get(training_obj, "description") or ""
                start_date = safe_get(training_obj, "start_date") or safe_get(training_obj, "scheduled_at")
                end_date = safe_get(training_obj, "end_date")
                mentor_name = safe_get(training_obj, "instructor") or safe_get(training_obj, "speaker") or "Training Lead"

            else:
                continue

            suitability_score = safe_get(alloc, "suitability_score") or 0.0
            alloc_status = safe_get(alloc, "status") or "assigned"

            results.append({
                "allocation_id": str(alloc.allocation_id),
                "reference_id": ref_id,
                "project_id": ref_id,  # Kept for frontend backwards compatibility
                "reference_type": ref_type,
                "title": title,
                "category": category,
                "role": safe_get(alloc, "role_on_project") or "Participant",
                "mentor": mentor_name,
                "project_status": str(target_status).lower(),
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