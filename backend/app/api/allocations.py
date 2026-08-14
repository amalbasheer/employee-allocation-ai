# app/api/allocations.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.api.deps import get_db
from app.models import Allocation
from app.schemas import AllocationResponse, AllocationCreate, AllocationUpdate

router = APIRouter()

@router.get("/", response_model=List[AllocationResponse])
def get_allocations(
    project_id: Optional[UUID] = Query(None, description="Filter allocations by project ID"),
    resource_id: Optional[UUID] = Query(None, description="Filter by resource (intern/employee) ID"),
    status: Optional[str] = Query(None, description="Filter by status: 'proposed', 'confirmed', 'rejected'"),
    db: Session = Depends(get_db)
):
    """List all allocations with optional filters for dashboard management."""
    query = db.query(Allocation)
    
    if project_id:
        query = query.filter(Allocation.project_id == project_id)
    if resource_id:
        query = query.filter(Allocation.resource_id == resource_id)
    if status:
        query = query.filter(Allocation.status == status)
        
    return query.all()

@router.post("/", response_model=AllocationResponse, status_code=status.HTTP_201_CREATED)
def create_allocation(allocation_in: AllocationCreate, db: Session = Depends(get_db)):
    """Manually allocate a resource (Intern/Employee) to a project or save an AI recommendation."""
    allocation = Allocation(**allocation_in.model_dump())
    db.add(allocation)
    db.commit()
    db.refresh(allocation)
    return allocation

@router.patch("/{allocation_id}", response_model=AllocationResponse)
def update_allocation_status(
    allocation_id: UUID,
    allocation_update: AllocationUpdate,
    db: Session = Depends(get_db)
):
    """Approve, reject, or change hours for an existing allocation (e.g., confirm a 'proposed' match)."""
    allocation = db.query(Allocation).filter(Allocation.allocation_id == allocation_id).first()
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation record not found")

    update_data = allocation_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(allocation, field, value)

    db.commit()
    db.refresh(allocation)
    return allocation

@router.delete("/{allocation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_allocation(allocation_id: UUID, db: Session = Depends(get_db)):
    """Remove/Deallocate a resource from a project, freeing up their weekly capacity hours."""
    allocation = db.query(Allocation).filter(Allocation.allocation_id == allocation_id).first()
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation record not found")

    db.delete(allocation)
    db.commit()
    return None