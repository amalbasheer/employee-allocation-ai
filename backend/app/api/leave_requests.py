from typing import List, Optional, Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from realtime import BaseModel
from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone, timedelta, date
from pydantic import BaseModel, Field
import sys
import re
from pathlib import Path

# Path to the shared root folder containing both backend and ai_engine
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from ai_engine.extraction import infer_skill_category
from ai_engine.embedding import generate_embedding
from app.database import get_db
from app.api.deps import require_admin
from app.models.employee import CompanyEmployee, EmployeeSkill, Availability
from app.models.taxonomy import Skill, LeaveRequest, Designation
from app.models.allocation import Allocation
from app.models.webinar import TrainingEngagement
from app.models.project import Project
from app.schemas.project import UserProfile
from app.schemas.employee import (
    CompanyEmployeeCreate,
    CompanyEmployeeResponse,
    CompanyEmployeeUpdate,
    EmployeeSkillCreate,
    EmployeeSkillResponse,
    EmployeeSkillUpdate,
    AvailabilityCreate,
    AvailabilityResponse,
    AvailabilityUpdate,
    DateRangeLeaveRequest,
    WeeklyBandwidthSummary,
    BatchAvailabilityUpdate,
    WeeklyBandwidthProjection,
    BandwidthForecastItem,
)

router = APIRouter()

class LeaveRequestResponse(BaseModel):
    request_id: str
    employee_id: Optional[str]
    employee_name: Optional[str] = "Unknown"
    employee_role: Optional[str] = "N/A"
    start_date: str
    end_date: str
    leave_type: str
    session: Optional[str] = "full_day"
    reason: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

def normalize_to_monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def generate_availability_id(db: Session) -> str:
    """
    Generates sequential availability IDs based on the highest existing ID.
    """
    # Fetch the lexicographically highest availability_id
    max_id = db.query(func.max(Availability.availability_id)).scalar()
    
    if not max_id:
        next_num = 1
    else:
        # Extract trailing numbers (e.g., 'rp2-avail-0005' -> 5)
        try:
            next_num = int(max_id.split("-")[-1]) + 1
        except (ValueError, IndexError):
            next_num = 1

    return f"rp2-avail-{next_num:04d}"

@router.get("/leave-requests", response_model=List[LeaveRequestResponse])
def get_all_leave_requests(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    """
    Fetch all leave requests for admin review with optional status filtering (PENDING, APPROVED, REJECTED).
    """
    query = (
        db.query(LeaveRequest, CompanyEmployee.name, Designation.title)
        .outerjoin(CompanyEmployee, LeaveRequest.employee_id == CompanyEmployee.employee_id)
        .outerjoin(Designation, CompanyEmployee.designation_id == Designation.designation_id)
    )

    if status_filter and status_filter.upper() != "ALL":
        query = query.filter(LeaveRequest.status == status_filter.upper())

    results = query.order_by(LeaveRequest.created_at.desc()).all()

    output = []
    for leave_req, emp_name, emp_role in results:
        output.append(
            LeaveRequestResponse(
                request_id=leave_req.request_id,
                employee_id=leave_req.employee_id,
                employee_name=emp_name or leave_req.employee_id,
                employee_role=emp_role or "Employee",
                start_date=str(leave_req.start_date),
                end_date=str(leave_req.end_date),
                leave_type=leave_req.leave_type,
                session=getattr(leave_req, "session", "full_day"),
                reason=leave_req.reason,
                status=leave_req.status,
                created_at=leave_req.created_at,
                # Dynamically use stored reviewer, fallback to "admin" if None (for older records)
                reviewed_by=leave_req.reviewed_by or "admin",
                reviewed_at=leave_req.reviewed_at,
            )
        )

    return output

class ReviewLeaveRequestPayload(BaseModel):
    status: Literal["APPROVED", "REJECTED"]

@router.put("/leave-requests/{request_id}/review", status_code=status.HTTP_200_OK)
def review_leave_request(
    request_id: str,
    payload: ReviewLeaveRequestPayload,
    db: Session = Depends(get_db),
):
    """
    Admin approval/rejection endpoint.
    Only executes schedule updates and availability changes when approved.
    """
    leave_req = db.query(LeaveRequest).filter(LeaveRequest.request_id == request_id).first()

    if not leave_req:
        raise HTTPException(status_code=404, detail="Leave request not found.")

    if leave_req.status != "PENDING":
        raise HTTPException(
            status_code=400, 
            detail=f"Leave request has already been processed with status: {leave_req.status}"
        )

    leave_req.status = payload.status
    leave_req.reviewed_by = 'admin'
    leave_req.reviewed_at = datetime.utcnow()

    # If rejected, commit status and return early without executing updates
    if payload.status == "REJECTED":
        db.commit()
        return {
            "status": "success",
            "message": f"Leave request {request_id} has been rejected."
        }

    # =========================================================================
    # EXECUTE OPERATIONS ONLY ON APPROVAL
    # =========================================================================
    employee_id = leave_req.employee_id
    start_date = leave_req.start_date
    end_date = leave_req.end_date

    # 1. PROCESS AVAILABILITY UPDATES
    start_monday = normalize_to_monday(start_date)
    end_monday = normalize_to_monday(end_date)
    current_monday = start_monday

    while current_monday <= end_monday:
        existing = (
            db.query(Availability)
            .filter(
                Availability.resource_id == employee_id,
                Availability.week_start_date == current_monday,
            )
            .first()
        )

        if leave_req.leave_type == "regular":
            calculated_available_hours = 0
            leave_days_count = 5
        else:
            # Urgent Leave: Compute non-leave working days
            work_days = [current_monday + timedelta(days=i) for i in range(5)]
            leave_days_count = sum(1 for d in work_days if start_date <= d <= end_date)
            calculated_available_hours = (5 - leave_days_count) * 8

        if existing:
            existing.available_hours = calculated_available_hours
            existing.is_on_leave = True
            existing.leave_reason = leave_req.reason
        else:
            new_avail = Availability(
                availability_id=generate_availability_id(db),
                resource_id=employee_id,
                resource_type="employee",
                week_start_date=current_monday,
                available_hours=calculated_available_hours,
                is_on_leave=True,
                leave_reason=leave_req.reason,
                session=leave_req.session,
            )
            db.add(new_avail)

        current_monday += timedelta(days=7)

    # 2. URGENT LEAVE SPECIFIC OPERATIONS (Mark Projects/Trainings On Leave)
    projects_updated = 0
    trainings_updated = 0

    if leave_req.leave_type == "urgent":
        # Mark Projects On Leave
        assigned_project_allocations = db.query(Allocation).filter(
            Allocation.resource_id == employee_id,
            Allocation.status == "assigned",
            Allocation.reference_type == "project",
        ).all()

        for alloc in assigned_project_allocations:
            project = db.query(Project).filter(
                Project.project_id == alloc.reference_id,
                Project.status == "in_progress",
            ).first()
            if project:
                project.status = "on_leave"
                alloc.status = "on_leave"
                projects_updated += 1

        # Mark Training Engagements On Leave
        assigned_training_allocations = db.query(Allocation).filter(
            Allocation.resource_id == employee_id,
            Allocation.status == "assigned",
            Allocation.reference_type == "training",
        ).all()

        for alloc in assigned_training_allocations:
            training = db.query(TrainingEngagement).filter(
                TrainingEngagement.engagement_id == alloc.reference_id,
                TrainingEngagement.status == "in_progress",
            ).first()
            if training:
                training.status = "on_leave"
                alloc.status = "on_leave"
                trainings_updated += 1

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to process approval: {str(e)}"
        )

    return {
        "status": "success",
        "message": f"Leave request {request_id} approved and schedule updated.",
        "projects_marked_on_leave": projects_updated,
        "trainings_marked_on_leave": trainings_updated,
    }
