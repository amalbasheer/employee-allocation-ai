# app/api/substitutions.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.api.deps import get_db
from app.models import Substitution, Allocation
from app.schemas.substitution import SubstitutionResponse, SubstitutionCreate, SubstitutionUpdate

router = APIRouter()

@router.get("/", response_model=List[SubstitutionResponse])
def get_substitutions(
    project_id: Optional[UUID] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List substitution requests with optional filters."""
    query = db.query(Substitution)
    if project_id:
        query = query.filter(Substitution.project_id == project_id)
    if status:
        query = query.filter(Substitution.status == status)
    return query.all()

@router.post("/", response_model=SubstitutionResponse, status_code=status.HTTP_201_CREATED)
def request_substitution(sub_in: SubstitutionCreate, db: Session = Depends(get_db)):
    """Request a replacement for an existing allocated resource on a project."""
    sub = Substitution(**sub_in.model_dump())
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub

@router.patch("/{substitution_id}", response_model=SubstitutionResponse)
def update_substitution_status(
    substitution_id: UUID,
    sub_update: SubstitutionUpdate,
    db: Session = Depends(get_db)
):
    """Approve or reject a substitution request."""
    sub = db.query(Substitution).filter(Substitution.substitution_id == substitution_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Substitution record not found")

    update_data = sub_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(sub, field, value)

    # If approved and replacement assigned, swap resource on active allocation
    if sub_update.status == "approved" and sub.replacement_resource_id:
        active_alloc = db.query(Allocation).filter(
            Allocation.project_id == sub.project_id,
            Allocation.resource_id == sub.original_resource_id
        ).first()
        
        if active_alloc:
            active_alloc.resource_id = sub.replacement_resource_id

    db.commit()
    db.refresh(sub)
    return sub