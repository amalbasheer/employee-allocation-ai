# app/api/allocations.py
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.allocation import Allocation, Substitution, AllocationLog
from app.schemas.allocation import (
    AllocationCreate,
    AllocationResponse,
    AllocationUpdate,
    SubstitutionCreate,
    SubstitutionUpdate,
    SubstitutionResponse,
    AllocationLogCreate,
    AllocationLogResponse,
)

router = APIRouter()


# Helper function to auto-record audit trail entries
def _log_allocation_change(db: Session, allocation_id: UUID, action: str, changed_by: str = "System"):
    log = AllocationLog(
        allocation_id=allocation_id,
        action=action,
        changed_by=changed_by
    )
    db.add(log)
    db.commit()


# ==========================================
# ALLOCATION LOG ENDPOINTS
# ==========================================
@router.get("/logs", response_model=List[AllocationLogResponse])
def get_all_logs(db: Session = Depends(get_db)):
    """Fetch history of all allocation decisions and status changes."""
    return db.query(AllocationLog).order_by(AllocationLog.timestamp.desc()).all()


@router.get("/logs/allocation/{allocation_id}", response_model=List[AllocationLogResponse])
def get_logs_for_allocation(allocation_id: UUID, db: Session = Depends(get_db)):
    """Fetch logs for a specific allocation record."""
    return (
        db.query(AllocationLog)
        .filter(AllocationLog.allocation_id == allocation_id)
        .order_by(AllocationLog.timestamp.desc())
        .all()
    )


@router.post("/logs", response_model=AllocationLogResponse, status_code=status.HTTP_201_CREATED)
def create_log(log_in: AllocationLogCreate, db: Session = Depends(get_db)):
    """Record a manual or system log entry."""
    alloc = db.query(Allocation).filter(Allocation.allocation_id == log_in.allocation_id).first()
    if not alloc:
        raise HTTPException(status_code=404, detail="Target allocation not found")

    log = AllocationLog(**log_in.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


# ==========================================
# SUBSTITUTION ENDPOINTS
# ==========================================
@router.get("/substitutions", response_model=List[SubstitutionResponse])
def get_substitutions(
    project_id: Optional[UUID] = Query(None, description="Filter by project UUID"),
    status: Optional[str] = Query(None, description="Filter by allocation status"),
    db: Session = Depends(get_db)
):
    """List substitution requests with optional filters using joined Allocation table."""
    query = db.query(Substitution)

    if project_id or status:
        query = query.join(Allocation, Substitution.original_allocation_id == Allocation.allocation_id)
        if project_id:
            query = query.filter(Allocation.project_id == project_id)
        if status:
            query = query.filter(Allocation.status == status)

    return query.all()


@router.post("/substitutions", response_model=SubstitutionResponse, status_code=status.HTTP_201_CREATED)
def request_substitution(sub_in: SubstitutionCreate, db: Session = Depends(get_db)):
    """Request a replacement for an existing allocated resource on a project."""
    alloc = db.query(Allocation).filter(Allocation.allocation_id == sub_in.original_allocation_id).first()
    if not alloc:
        raise HTTPException(status_code=404, detail="Original allocation record not found")

    sub = Substitution(**sub_in.model_dump())
    db.add(sub)
    db.commit()
    db.refresh(sub)

    # Log substitution request
    _log_allocation_change(
        db=db,
        allocation_id=alloc.allocation_id,
        action=f"Substitution requested with resource '{sub.substitute_resource_id}' ({sub.substitute_resource_type}). Reason: {sub.reason}"
    )

    return sub


@router.patch("/substitutions/{substitution_id}", response_model=SubstitutionResponse)
def update_substitution_status(
    substitution_id: UUID,
    sub_update: SubstitutionUpdate,
    db: Session = Depends(get_db)
):
    """Approve or reject a substitution request and swap active resource if approved."""
    sub = db.query(Substitution).filter(Substitution.substitution_id == substitution_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Substitution record not found")

    alloc = db.query(Allocation).filter(Allocation.allocation_id == sub.original_allocation_id).first()

    if alloc and sub_update.status:
        # Update allocation status (e.g. 'approved', 'substituted', 'rejected')
        alloc.status = sub_update.status

        # If approved, perform the resource swap on the target allocation
        if sub_update.status.lower() in ["approved", "substituted"]:
            old_resource_id = alloc.resource_id
            alloc.resource_id = sub.substitute_resource_id
            alloc.resource_type = sub.substitute_resource_type

            _log_allocation_change(
                db=db,
                allocation_id=alloc.allocation_id,
                action=f"Substitution approved. Swapped resource from '{old_resource_id}' to '{sub.substitute_resource_id}'"
            )

    db.commit()
    db.refresh(sub)
    return sub


# ==========================================
# ALLOCATION CRUD ENDPOINTS
# ==========================================
@router.get("", response_model=List[AllocationResponse])
def get_allocations(
    project_id: Optional[UUID] = Query(None, description="Filter allocations by project ID"),
    resource_id: Optional[UUID] = Query(None, description="Filter allocations by resource ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter allocations by status"),
    db: Session = Depends(get_db)
):
    """Fetch allocations with optional filtering by project, resource, or status."""
    query = db.query(Allocation)

    if project_id:
        query = query.filter(Allocation.project_id == project_id)
    if resource_id:
        query = query.filter(Allocation.resource_id == resource_id)
    if status_filter:
        query = query.filter(Allocation.status == status_filter)

    allocations = query.all()

    for alloc in allocations:
        alloc.substitutions = (
            db.query(Substitution)
            .filter(Substitution.original_allocation_id == alloc.allocation_id)
            .all()
        )
        alloc.logs = (
            db.query(AllocationLog)
            .filter(AllocationLog.allocation_id == alloc.allocation_id)
            .order_by(AllocationLog.timestamp.desc())
            .all()
        )

    return allocations


@router.post("", response_model=AllocationResponse, status_code=status.HTTP_201_CREATED)
def create_allocation(alloc_in: AllocationCreate, db: Session = Depends(get_db)):
    """Create a new resource allocation and automatically write an initial audit log entry."""
    new_alloc = Allocation(**alloc_in.model_dump())
    db.add(new_alloc)
    db.commit()
    db.refresh(new_alloc)

    _log_allocation_change(
        db=db,
        allocation_id=new_alloc.allocation_id,
        action=f"Allocation created with status '{new_alloc.status}'",
        changed_by=new_alloc.assigned_by
    )

    new_alloc.substitutions = []
    new_alloc.logs = (
        db.query(AllocationLog)
        .filter(AllocationLog.allocation_id == new_alloc.allocation_id)
        .all()
    )
    return new_alloc


@router.get("/{allocation_id}", response_model=AllocationResponse)
def get_allocation_by_id(allocation_id: UUID, db: Session = Depends(get_db)):
    """Fetch a single allocation along with its substitutions and audit history."""
    alloc = db.query(Allocation).filter(Allocation.allocation_id == allocation_id).first()
    if not alloc:
        raise HTTPException(status_code=404, detail="Allocation not found")

    alloc.substitutions = (
        db.query(Substitution)
        .filter(Substitution.original_allocation_id == allocation_id)
        .all()
    )
    alloc.logs = (
        db.query(AllocationLog)
        .filter(AllocationLog.allocation_id == allocation_id)
        .order_by(AllocationLog.timestamp.desc())
        .all()
    )
    return alloc


@router.patch("/{allocation_id}", response_model=AllocationResponse)
def update_allocation(
    allocation_id: UUID,
    alloc_in: AllocationUpdate,
    changed_by: str = Query("System", description="Name/ID of user or process making the change"),
    db: Session = Depends(get_db)
):
    """Update allocation details and record what fields changed in allocation_logs."""
    alloc = db.query(Allocation).filter(Allocation.allocation_id == allocation_id).first()
    if not alloc:
        raise HTTPException(status_code=404, detail="Allocation not found")

    update_data = alloc_in.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    changed_fields = []
    for field, value in update_data.items():
        old_val = getattr(alloc, field)
        if old_val != value:
            changed_fields.append(f"{field}: '{old_val}' -> '{value}'")
            setattr(alloc, field, value)

    db.commit()
    db.refresh(alloc)

    if changed_fields:
        action_summary = f"Updated fields: {', '.join(changed_fields)}"
        _log_allocation_change(db=db, allocation_id=allocation_id, action=action_summary, changed_by=changed_by)

    alloc.substitutions = (
        db.query(Substitution)
        .filter(Substitution.original_allocation_id == allocation_id)
        .all()
    )
    alloc.logs = (
        db.query(AllocationLog)
        .filter(AllocationLog.allocation_id == allocation_id)
        .order_by(AllocationLog.timestamp.desc())
        .all()
    )
    return alloc


@router.delete("/{allocation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_allocation(allocation_id: UUID, db: Session = Depends(get_db)):
    """Delete an allocation record."""
    alloc = db.query(Allocation).filter(Allocation.allocation_id == allocation_id).first()
    if not alloc:
        raise HTTPException(status_code=404, detail="Allocation not found")

    db.delete(alloc)
    db.commit()
    return None