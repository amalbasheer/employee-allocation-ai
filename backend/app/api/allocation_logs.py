# app/api/allocation_logs.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.api.deps import get_db
from app.models import AllocationLog
from app.schemas.allocation_log import AllocationLogResponse, AllocationLogCreate

router = APIRouter()

@router.get("/", response_model=List[AllocationLogResponse])
def get_all_logs(db: Session = Depends(get_db)):
    """Fetch history of all allocation decisions and status changes."""
    return db.query(AllocationLog).order_by(AllocationLog.created_at.desc()).all()

@router.get("/allocation/{allocation_id}", response_model=List[AllocationLogResponse])
def get_logs_for_allocation(allocation_id: UUID, db: Session = Depends(get_db)):
    """Fetch logs for a specific allocation record."""
    return db.query(AllocationLog).filter(AllocationLog.allocation_id == allocation_id).all()

@router.post("/", response_model=AllocationLogResponse)
def create_log(log_in: AllocationLogCreate, db: Session = Depends(get_db)):
    """Record a manual or system log entry."""
    log = AllocationLog(**log_in.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    return log