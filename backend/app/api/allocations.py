import uuid
import traceback
from datetime import datetime, timezone
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, select
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel

from app.api.deps import get_db, get_current_user, require_admin
from app.models.allocation import Allocation, AllocationLog, Substitution
from app.models.project import Project, ProjectRequirement
from app.models.webinar import TrainingEngagement, StudentBatch
from app.models.taxonomy import Skill
from app.models.employee import CompanyEmployee
from app.models.intern import InternsAndStudents
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
def generate_next_allocation_id(db: Session) -> str:
    # Fetch all allocation IDs matching the prefix
    alloc_ids = db.scalars(
        select(Allocation.allocation_id).filter(Allocation.allocation_id.like("rp2-alloc-%"))
    ).all()
    
    max_num = 0
    for alloc_id in alloc_ids:
        parts = alloc_id.split("-")
        if parts[-1].isdigit():
            max_num = max(max_num, int(parts[-1]))
            
    return f"rp2-alloc-{max_num + 1:04d}"

def generate_next_log_id(db: Session) -> str:
    """Safely extracts the maximum numeric suffix from allocation_logs to generate rp2-log-XXXX."""
    records = db.query(AllocationLog.log_id).filter(
        AllocationLog.log_id.like("rp2-log-%")
    ).all()

    max_num = 0
    for (log_id,) in records:
        if log_id:
            parts = str(log_id).split("-")
            if parts[-1].isdigit():
                max_num = max(max_num, int(parts[-1]))

    return f"rp2-log-{max_num + 1:04d}"

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

    # Generate custom formatted primary key
    new_alloc_id = generate_next_allocation_id(db)

    # 2. Create the Allocation record
    new_allocation = Allocation(
        allocation_id=new_alloc_id,  # Set formatted primary key here
        reference_id=payload.reference_id,
        reference_type=payload.reference_type.lower().strip(),
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        role_on_project=payload.role_on_project,
        allocated_hours=payload.allocated_hours,
        suitability_score=payload.suitability_score,
        status="proposed",
        assigned_by=admin_user.name,
        assigned_at=datetime.now(timezone.utc)
    )
    # --- CATCH EXACT DATABASE ERROR HERE ---
    try:
        db.add(new_allocation)
        db.flush()  # Populates new_allocation.allocation_id for the audit log
    except IntegrityError as e:
        db.rollback()
        print("================ EXACT DB DRIVER ERROR ================")
        print(e.orig)
        print("=======================================================")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database constraint error: {str(e.orig)}"
        )
    # --------------------------------------

    # 3. Create Audit Log entry
    new_log_id = generate_next_log_id(db)

    log = AllocationLog(
        log_id=new_log_id,
        allocation_id=new_allocation.allocation_id,
        action="PROPOSED",
        changed_by=admin_user.name,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(log)

    # 4. Commit transaction
    db.commit()
    db.refresh(new_allocation)

    return new_allocation

# -------------------------------------------------------------------
# ASSIGNING PROJECT TO INTERN BY ADMIN
# -------------------------------------------------------------------

# Pydantic Schema for Student Assignment Request
class StudentAssignRequest(BaseModel):
    reference_id: str  # e.g., 'rp2-proj-0006' (Project ID)
    resource_id: str
    resource_type: str = "intern"    # Unique ID of the student
    reference_type: Optional[str] = "project"
    role_on_project: Optional[str] = "Student Contributor"
    allocated_hours: Optional[int] = 10
    suitability_score: Optional[float] = 0.0

@router.post("/assign-student", response_model=AllocationResponse, status_code=status.HTTP_201_CREATED)
def assign_student(
    payload: StudentAssignRequest,
    db: Session = Depends(get_db),
    admin_user: UserProfile = Depends(require_admin)
):
    clean_ref_id = payload.reference_id.strip()
    clean_student_id = payload.resource_id.strip()

    # 1. Prevent duplicate active assignments for the same student on this project
    existing_allocation = (
        db.query(Allocation)
        .filter(
            Allocation.reference_id == clean_ref_id,
            Allocation.resource_id == clean_student_id,
            Allocation.resource_type == "intern",
            Allocation.status.in_(["assigned", "proposed", "accepted"])
        )
        .first()
    )

    if existing_allocation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Student '{clean_student_id}' is already assigned or proposed for this project."
        )

    # 2. Create the new Allocation directly with status='assigned'
    new_allocation = Allocation(
        allocation_id=generate_next_allocation_id(db),
        reference_id=clean_ref_id,
        reference_type=payload.reference_type,
        resource_type="intern",
        resource_id=clean_student_id,
        role_on_project=payload.role_on_project,
        allocated_hours=payload.allocated_hours,
        suitability_score=payload.suitability_score,
        status="assigned",  # Directly assigned without requiring student acceptance phase
        assigned_by=admin_user.name,
        assigned_at=datetime.now(timezone.utc)
    )
    db.add(new_allocation)
    db.flush()

    # 3. Create Audit Log
    log = AllocationLog(
        log_id=generate_next_log_id(db),
        allocation_id=new_allocation.allocation_id,
        action="STUDENT_ASSIGNED",
        changed_by=admin_user.name,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(log)

    db.commit()
    db.refresh(new_allocation)

    return new_allocation

# -------------------------------------------------------------------
# CONFIRMATION BY ADMIN (Updated for Substitution Support)
# -------------------------------------------------------------------
@router.patch("/{identifier}/assign", response_model=AllocationResponse)
def assign_allocation(
    identifier: str,
    db: Session = Depends(get_db),
    admin_user: UserProfile = Depends(require_admin)
):
    clean_id = identifier.strip()

    # 1. First attempt direct lookup by unique allocation_id
    allocation = (
        db.query(Allocation)
        .filter(func.lower(Allocation.allocation_id) == clean_id.lower())
        .first()
    )

    # 2. If identifier is a reference_id (Project ID), look specifically for pending proposals ('accepted' or 'proposed')
    if not allocation:
        allocation = (
            db.query(Allocation)
            .filter(
                func.lower(Allocation.reference_id) == clean_id.lower(),
                func.lower(Allocation.resource_type).in_(["employee", "mentor"]),
                Allocation.status.in_(["accepted", "proposed"])  # FIX 1: Filter only pending proposals
            )
            .order_by(Allocation.allocation_id.desc())
            .first()
        )

    if not allocation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No pending employee/mentor allocation found for matching ID or Reference '{clean_id}'."
        )

    prev_status = str(allocation.status).lower().strip()

    # 3. Validation for Employee / Mentor assignment
    valid_statuses = ["accepted", "proposed"]
    if prev_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot confirm mentor assignment for allocation '{allocation.allocation_id}'. Current status is '{prev_status}', expected 'accepted' or 'proposed'."
        )

    ref_type = str(getattr(allocation, "reference_type", "project") or "project").lower().strip()
    ref_id = getattr(allocation, "reference_id", None) or getattr(allocation, "project_id", None)
    resource_type = str(getattr(allocation, "resource_type", "employee")).lower().strip()

    # 4. FIX 2: Deactivate any previous active allocations for this project (Substitution Handling)
    if ref_id:
        previous_active_allocations = (
            db.query(Allocation)
            .filter(
                func.lower(Allocation.reference_id) == clean_id.lower(),
                Allocation.allocation_id != allocation.allocation_id,
                Allocation.status == "assigned"
            )
            .all()
        )
        for old_alloc in previous_active_allocations:
            old_alloc.status = "replaced"  # Or "revoked" / "cancelled"

    # 5. Transition target allocation status to assigned
    allocation.status = "assigned"

    # 6. Update linked target entity (Project / Batch / Training)
    if ref_type == "project" and ref_id:
        project = db.query(Project).filter(Project.project_id == ref_id).first()
        if project:
            project.status = "in_progress"
            if hasattr(project, "mentor_id"):
                project.mentor_id = str(allocation.resource_id)  # Updates project mentor link if column exists

    elif ref_type in ["batch", "student_batch", "studentbatch"] and ref_id:
        batch_obj = db.query(StudentBatch).filter(StudentBatch.batch_id == ref_id).first()
        if batch_obj and resource_type in ["employee", "mentor"]:
            batch_obj.mentor_id = str(allocation.resource_id)

    elif ref_type in ["training", "webinar", "engagement"] and ref_id:
        training_obj = db.query(TrainingEngagement).filter(TrainingEngagement.engagement_id == ref_id).first()
        if training_obj:
            training_obj.status = "in_progress"

    # 7. Create Audit Log
    log = AllocationLog(
        log_id=generate_next_log_id(db),
        allocation_id=allocation.allocation_id,
        action="ASSIGNED",
        changed_by=admin_user.name,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(log)
    db.commit()
    db.refresh(allocation)

    return allocation

# -------------------------------------------------------------------
# 2. STATUS TRANSITION (ACCEPT / REJECT / ASSIGN)
# -------------------------------------------------------------------
@router.patch("/{identifier}/status", response_model=AllocationResponse)
def update_allocation_status(
    identifier: str,  # Accepts either 'rp2-proj-0002' (reference_id) OR 'rp2-alloc-0007' (allocation_id)
    payload: AllocationStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    clean_id = identifier.strip()
    # Search by reference_id first, falling back to allocation_id
    allocation = db.query(Allocation).filter(
        or_(
            func.lower(Allocation.allocation_id) == clean_id.lower(),
            func.lower(Allocation.reference_id) == clean_id.lower(),
        )
    ).first()

    if not allocation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Allocation with Reference or Allocation ID '{clean_id}' not found."
        )

    user_role = str(getattr(current_user, "role", "")).lower()
    prev_status = str(allocation.status).lower()
    target_status = str(payload.status).lower()

    # Identify reference parameters
    ref_type = str(getattr(allocation, "reference_type", "project") or "project").lower().strip()
    ref_id = getattr(allocation, "reference_id", None) or getattr(allocation, "project_id", None)
    resource_type = str(getattr(allocation, "resource_type", "employee")).lower().strip()

    # --- ADMIN / SUPERADMIN ACTION ---
    if user_role in ["admin", "superadmin"]:
        if target_status == "assigned":
            if resource_type in ["employee", "mentor"] and prev_status != "accepted":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot confirm assignment. Current status is '{prev_status}', but employee must accept first."
                )
            
            allocation.status = "assigned"

            # Dynamic Target Entity Status Update
            if ref_type == "project" and ref_id:
                project = db.query(Project).filter(Project.project_id == ref_id).first()
                if project:
                    project.status = "in_progress"

            elif ref_type in ["batch", "student_batch", "studentbatch"] and ref_id:
                batch_obj = db.query(StudentBatch).filter(StudentBatch.batch_id == ref_id).first()
                if batch_obj and resource_type in ["employee", "mentor"]:
                    batch_obj.mentor_id = str(allocation.resource_id)

            elif ref_type in ["training", "webinar", "engagement"] and ref_id:
                training_obj = db.query(TrainingEngagement).filter(TrainingEngagement.engagement_id == ref_id).first()
                if training_obj:
                    training_obj.status = "in_progress"

        elif target_status in ["cancelled", "proposed", "completed"]:
            allocation.status = target_status
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Invalid target status '{target_status}' for Admin action."
            )

    # --- EMPLOYEE / MENTOR ACTION ---
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
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Unauthorized role to perform this action."
        )

    # Audit Logging: Upper-case target status in log table
    log = AllocationLog(
        log_id=generate_next_log_id(db),
        allocation_id=allocation.allocation_id,
        action=target_status.upper(),
        changed_by=getattr(current_user, "name", "System User"),
        timestamp=datetime.now(timezone.utc)
    )
    db.add(log)
    db.commit()
    db.refresh(allocation)

    return allocation

# -------------------------------------------------------------------
# 1. EMPLOYEE ACCEPTING THE PROPOSAL
# -------------------------------------------------------------------
class AllocationRespondRequest(BaseModel):
    status: str          # "accepted" or "rejected_by_employee"
    employee_id: str


@router.patch("/{allocation_id}/respond")
def accept_allocation(
    allocation_id: str,
    payload: AllocationRespondRequest,
    db: Session = Depends(get_db)
):
    # 1. Fetch allocation record specifically for resource_type = 'employee'
    allocation = (
        db.query(Allocation)
        .filter(
            Allocation.allocation_id == allocation_id,
            func.lower(Allocation.resource_type) == "employee"
        )
        .first()
    )
    if not allocation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Employee allocation '{allocation_id}' not found."
        )

    # 2. Update allocation status
    formatted_status = payload.status.lower()
    allocation.status = formatted_status

    # 3. Reference Type Differentiation & Status Syncing
    ref_type = (allocation.reference_type or '').lower()

    if ref_type in ['training_engagement', 'training', 'webinar', 'workshop']:
        engagement = (
            db.query(TrainingEngagement)
            .filter(func.lower(TrainingEngagement.engagement_id) == allocation.reference_id.lower())
            .first()
        )
        if engagement:
            engagement.status = formatted_status

    elif ref_type == 'project':
        # Project lifecycle status is independent of single resource acceptance
        pass

    # 4. Create Audit Log entry
    new_log_id = generate_next_log_id(db)
    
    log = AllocationLog(
        log_id=new_log_id,
        allocation_id=allocation_id,
        action=formatted_status.upper(),
        changed_by=payload.employee_id,
        timestamp=datetime.now(timezone.utc)
    )

    db.add(log)
    db.commit()
    db.refresh(allocation)

    return {
        "status": "success",
        "message": f"Proposal marked as {formatted_status}",
        "allocation_id": allocation.allocation_id,
        "current_status": allocation.status
    }


# -------------------------------------------------------------------
# 2. EMPLOYEE REJECTING THE PROPOSAL
# -------------------------------------------------------------------
@router.patch("/{allocation_id}/reject")
def reject_allocation(
    allocation_id: str,
    payload: AllocationRespondRequest,
    db: Session = Depends(get_db)
):
    # 1. Fetch allocation record specifically for resource_type = 'employee'
    allocation = (
        db.query(Allocation)
        .filter(
            Allocation.allocation_id == allocation_id,
            func.lower(Allocation.resource_type) == "employee"
        )
        .first()
    )
    if not allocation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Employee allocation '{allocation_id}' not found."
        )

    # 2. Update allocation status
    formatted_status = payload.status.lower()
    allocation.status = formatted_status

    # 3. Reference Type Differentiation & Status Syncing
    ref_type = (allocation.reference_type or '').lower()

    if ref_type in ['training_engagement', 'training', 'webinar', 'workshop']:
        training_item = (
            db.query(TrainingEngagement)
            .filter(func.lower(TrainingEngagement.engagement_id) == allocation.reference_id.lower())
            .first()
        )
        if training_item:
            training_item.status = formatted_status

    elif ref_type == 'project':
        # Project lifecycle status remains unchanged on individual resource rejection
        pass

    # 4. Create Audit Log entry
    new_log_id = generate_next_log_id(db)
    
    log = AllocationLog(
        log_id=new_log_id,
        allocation_id=allocation_id,
        action='REJECTED',
        changed_by=payload.employee_id,
        timestamp=datetime.now(timezone.utc)
    )

    db.add(log)
    db.commit()
    db.refresh(allocation)

    return {
        "status": "success",
        "message": f"Proposal marked as {formatted_status}",
        "allocation_id": allocation.allocation_id,
        "current_status": allocation.status
    }


# -------------------------------------------------------------------
# 3. SUBSTITUTE REJECTED ALLOCATION (ADMIN)
# -------------------------------------------------------------------
def generate_next_sub_id(db: Session) -> str:
    sub_ids = db.scalars(
        select(Substitution.substitution_id).filter(Substitution.substitution_id.like("rp2-sub-%"))
    ).all()
    
    max_num = 0
    for sub_id in sub_ids:
        parts = sub_id.split("-")
        if parts[-1].isdigit():
            max_num = max(max_num, int(parts[-1]))
            
    return f"rp2-sub-{max_num + 1:04d}"


@router.post("/{reference_id}/substitute", response_model=SubstitutionResponse, status_code=status.HTTP_201_CREATED)
def substitute_allocation(
    reference_id: str,
    payload: SubstituteRequest,
    db: Session = Depends(get_db),
    admin_user: UserProfile = Depends(require_admin)
):
    clean_ref_id = reference_id.strip()

    # 1. Fetch latest allocation for this reference_id ONLY where resource_type = 'employee'
    orig_allocation = (
        db.query(Allocation)
        .filter(
            func.lower(Allocation.reference_id) == clean_ref_id.lower(),
            func.lower(Allocation.resource_type) == "employee"
        )
        .order_by(Allocation.allocation_id.desc())
        .first()
    )

    if not orig_allocation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Original employee allocation record for reference_id '{clean_ref_id}' not found."
        )

    # 2. Mark original allocation as SUBSTITUTED
    orig_allocation.status = "substituted"

    # 3. Dynamic Reference Type handling & linked entity status update
    ref_type = (orig_allocation.reference_type or "project").lower()

    if ref_type in ['training_engagement', 'training', 'webinar', 'workshop']:
        training_item = (
            db.query(TrainingEngagement)
            .filter(func.lower(TrainingEngagement.engagement_id) == clean_ref_id.lower())
            .first()
        )
        if training_item:
            training_item.status = "proposed"

    elif ref_type == 'project':
        # Project entity lifecycle status remains independent of individual resource substitutions
        pass

    # 4. Record substitution details
    sub_record = Substitution(
        substitution_id=generate_next_sub_id(db),
        original_allocation_id=orig_allocation.allocation_id,
        substitute_resource_type=payload.substitute_resource_type,
        substitute_resource_id=payload.substitute_resource_id,
        reason=payload.reason,
        created_at=datetime.now(timezone.utc)
    )
    db.add(sub_record)

    # 5. Create replacement allocation in PROPOSED state
    new_allocation = Allocation(
        allocation_id=generate_next_allocation_id(db),
        reference_id=orig_allocation.reference_id,
        reference_type=orig_allocation.reference_type,
        resource_type=payload.substitute_resource_type,
        resource_id=payload.substitute_resource_id,
        role_on_project=orig_allocation.role_on_project,
        allocated_hours=orig_allocation.allocated_hours,
        suitability_score=orig_allocation.suitability_score,
        status="proposed",
        assigned_by=admin_user.name, 
        assigned_at=datetime.now(timezone.utc)
    )
    db.add(new_allocation)
    db.flush()

    # 6. Log changes into allocation_log
    log = AllocationLog(
        log_id=generate_next_log_id(db),
        allocation_id=orig_allocation.allocation_id,
        action="SUBSTITUTED",
        changed_by=admin_user.name,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(log)

    db.commit()
    db.refresh(sub_record)
    return sub_record

@router.get("/my-allocations")
def get_my_allocations(
    resource_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Query allocations for the current logged-in user (Intern or Employee).
    - Returns mentor name for intern allocations.
    - Returns assigned students/interns (names & IDs) for employee/mentor allocations.
    """
    try:
        # -------------------------------------------------------
        # Helper 1: Extract Name from any User/Employee/Student Record
        # -------------------------------------------------------
        def get_full_name(entity: Any) -> Optional[str]:
            if not entity:
                return None
            full = safe_get(entity, "full_name") or safe_get(entity, "name")
            if full and str(full).strip():
                return str(full).strip()
            first = safe_get(entity, "first_name", "") or ""
            last = safe_get(entity, "last_name", "") or ""
            combined = f"{first} {last}".strip()
            return combined if combined else None

        # -------------------------------------------------------
        # Helper 2: Safe Check if Class is a SQLAlchemy Model
        # -------------------------------------------------------
        def is_sqlalchemy_model(cls) -> bool:
            return isinstance(cls, type) and hasattr(cls, "__table__")

        # -------------------------------------------------------
        # Helper 3: Resolve Person Name by Resource ID
        # -------------------------------------------------------
        def resolve_person_name(res_id: str) -> str:
            if not res_id:
                return "Unknown User"

            # 1. Check CompanyEmployee Table
            if "CompanyEmployee" in globals() and is_sqlalchemy_model(CompanyEmployee):
                emp = db.query(CompanyEmployee).filter(
                    CompanyEmployee.employee_id == str(res_id)
                ).first()
                emp_name = get_full_name(emp)
                if emp_name:
                    return emp_name

            # 2. Check Student/Intern Table (only if valid SQLAlchemy model)
            if "Student" in globals() and is_sqlalchemy_model(InternsAndStudents):
                student = db.query(InternsAndStudents).filter(
                    (InternsAndStudents.intern_id == str(res_id)) | 
                    (InternsAndStudents.student_id == str(res_id)) | 
                    (InternsAndStudents.id == str(res_id))
                ).first()
                std_name = get_full_name(student)
                if std_name:
                    return std_name

            # 3. Check UserProfile Model (only if valid SQLAlchemy model)
            if "UserProfile" in globals() and is_sqlalchemy_model(UserProfile):
                user = db.query(UserProfile).filter(
                    (UserProfile.user_id == str(res_id)) | 
                    (UserProfile.id == str(res_id))
                ).first()
                usr_name = get_full_name(user)
                if usr_name:
                    return usr_name

            return f"Resource ({res_id})"

        # -------------------------------------------------------
        # 1. Collect Valid User IDs from Auth / Query Param
        # -------------------------------------------------------
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

        # -------------------------------------------------------
        # 2. Query Allocations for Current User
        # -------------------------------------------------------
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

            # Defaults
            title = "Assigned Engagement"
            category = "General"
            target_status = "open"
            description = ""
            start_date = None
            end_date = None
            tech_stack = []
            mentor_name = "Pending Mentor Assignment"
            assigned_students = []
            assigned_student_names = []

            # -------------------------------------------------------
            # A. PROJECT REFERENCE
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

                # Tech Stack
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

                # --- 1. RESOLVE MENTOR (For Intern Dashboard) ---
                direct_mentor_id = safe_get(project_obj, "mentor_id")
                if direct_mentor_id:
                    mentor_name = resolve_person_name(str(direct_mentor_id))

                if mentor_name == "Pending Mentor Assignment":
                    mentor_alloc = db.query(Allocation).filter(
                        Allocation.reference_id == ref_id,
                        func.lower(Allocation.reference_type) == "project",
                        func.lower(Allocation.resource_type).in_(["employee", "mentor"]),
                        ~Allocation.resource_id.in_(valid_ids)
                    ).first()

                    if mentor_alloc and mentor_alloc.resource_id:
                        mentor_name = resolve_person_name(str(mentor_alloc.resource_id))

                # --- 2. RESOLVE ASSIGNED STUDENTS / INTERNS (For Employee Dashboard) ---
                student_allocs = db.query(Allocation).filter(
                    Allocation.reference_id == ref_id,
                    func.lower(Allocation.reference_type) == "project",
                    func.lower(Allocation.resource_type).in_(["intern", "student", "mentee"]),
                    ~Allocation.resource_id.in_(valid_ids)
                ).all()

                for s_alloc in student_allocs:
                    s_id = str(s_alloc.resource_id)
                    s_name = resolve_person_name(s_id)
                    assigned_students.append({
                        "id": s_id,
                        "name": s_name,
                        "role": safe_get(s_alloc, "role_on_project") or "Intern",
                        "status": safe_get(s_alloc, "status") or "assigned"
                    })
                    assigned_student_names.append(s_name)

            # -------------------------------------------------------
            # B. BATCH REFERENCE
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
            # C. TRAINING REFERENCE
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
                "project_id": ref_id,
                "reference_type": ref_type,
                "title": title,
                "category": category,
                "role": safe_get(alloc, "role_on_project") or "Participant",
                "mentor": mentor_name,
                "mentor_name": mentor_name,
                "assigned_students": assigned_students,
                "assigned_student_names": assigned_student_names,
                "assigned_students_count": len(assigned_students),
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