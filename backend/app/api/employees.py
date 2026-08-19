# app/api/employees.py
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone, timedelta, date

from app.database import get_db
from app.models.employee import CompanyEmployee, EmployeeSkill, Availability
from app.models.allocation import Allocation
from app.models.project import Project
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


# ==========================================
# EMPLOYEE ENDPOINTS
# ==========================================
@router.get("", response_model=List[CompanyEmployeeResponse])
def get_employees(db: Session = Depends(get_db)):
    """Fetch all employees with their assigned skills."""
    employees = db.query(CompanyEmployee).all()
    
    for emp in employees:
        emp.skills = (
            db.query(EmployeeSkill)
            .filter(EmployeeSkill.employee_id == emp.employee_id)
            .all()
        )
    return employees

@router.post("", response_model=CompanyEmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(employee_in: CompanyEmployeeCreate, db: Session = Depends(get_db)):
    """Create a new employee record (optionally with initial skills)."""
    
    # 1. Unique email check
    existing = db.query(CompanyEmployee).filter(CompanyEmployee.email == employee_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An employee with email '{employee_in.email}' already exists."
        )

    # 2. Extract payload and convert empty string designation_id to None
    emp_data = employee_in.model_dump(exclude={"skills"})
    
    if emp_data.get("designation_id") == "":
        emp_data["designation_id"] = None

    # Automatically add created_at timestamp if missing
    if "created_at" not in emp_data or emp_data["created_at"] is None:
        emp_data["created_at"] = datetime.now(timezone.utc)
    
    try:
        new_employee = CompanyEmployee(**emp_data)
        db.add(new_employee)
        db.commit()
        db.refresh(new_employee)

        # 3. Process nested skills if provided
        created_skills = []
        if employee_in.skills:
            for skill in employee_in.skills:
                db_skill = EmployeeSkill(
                    employee_id=new_employee.employee_id,
                    **skill.model_dump()
                )
                db.add(db_skill)
                created_skills.append(db_skill)
            
            db.commit()
            for skill in created_skills:
                db.refresh(skill)

        new_employee.skills = created_skills
        return new_employee

    except IntegrityError as e:
        db.rollback()
        # Catches foreign key failure (e.g. designation_id doesn't exist) or missing required columns
        error_msg = str(e.orig)
        if "designation" in error_msg.lower() or "foreign key" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected designation_id does not exist in the database."
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database integrity error: {error_msg}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create employee: {str(e)}"
        )


@router.get("/{employee_id}", response_model=CompanyEmployeeResponse)
def get_employee_by_id(employee_id: str, db: Session = Depends(get_db)):
    """Fetch a single employee by UUID."""
    employee = db.query(CompanyEmployee).filter(CompanyEmployee.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    employee.skills = (
        db.query(EmployeeSkill)
        .filter(EmployeeSkill.employee_id == employee_id)
        .all()
    )
    return employee


@router.patch("/{employee_id}", response_model=CompanyEmployeeResponse)
def update_employee(employee_id: str, employee_in: CompanyEmployeeUpdate, db: Session = Depends(get_db)):
    """Update employee profile details."""
    employee = db.query(CompanyEmployee).filter(CompanyEmployee.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    update_data = employee_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(employee, field, value)

    db.commit()
    db.refresh(employee)

    employee.skills = (
        db.query(EmployeeSkill)
        .filter(EmployeeSkill.employee_id == employee_id)
        .all()
    )
    return employee


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(employee_id: str, db: Session = Depends(get_db)):
    """Delete an employee (Cascade drops associated skills)."""
    employee = db.query(CompanyEmployee).filter(CompanyEmployee.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    db.delete(employee)
    db.commit()
    return None


# ==========================================
# EMPLOYEE SKILLS ENDPOINTS (Composite PK)
# ==========================================
@router.post("/{employee_id}/skills", response_model=EmployeeSkillResponse, status_code=status.HTTP_201_CREATED)
def add_employee_skill(employee_id: str, skill_in: EmployeeSkillCreate, db: Session = Depends(get_db)):
    """Add or update a skill link for an employee."""
    employee = db.query(CompanyEmployee).filter(CompanyEmployee.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Check if this skill link already exists
    existing_skill = db.query(EmployeeSkill).filter(
        EmployeeSkill.employee_id == employee_id,
        EmployeeSkill.skill_id == skill_in.skill_id
    ).first()

    if existing_skill:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This skill is already assigned to the employee."
        )

    skill_data = skill_in.model_dump(exclude={"employee_id"})
    new_skill = EmployeeSkill(employee_id=employee_id, **skill_data)

    db.add(new_skill)
    db.commit()
    db.refresh(new_skill)
    return new_skill


@router.delete("/{employee_id}/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_employee_skill(employee_id: str, skill_id: str, db: Session = Depends(get_db)):
    """Remove a skill link from an employee using composite primary keys."""
    skill_entry = db.query(EmployeeSkill).filter(
        EmployeeSkill.employee_id == employee_id,
        EmployeeSkill.skill_id == skill_id
    ).first()

    if not skill_entry:
        raise HTTPException(status_code=404, detail="Employee skill entry not found")

    db.delete(skill_entry)
    db.commit()
    return None


# ==========================================
# AVAILABILITY ENDPOINTS
# ==========================================
def normalize_to_monday(d: date) -> date:
    return d - timedelta(days=d.weekday())

def generate_availability_id(db: Session) -> str:
    """
    Generates sequential availability IDs in the format: rp2-avail-0001
    """
    # Get the total count of availability records to determine the next index
    count = db.query(func.count(Availability.availability_id)).scalar() or 0
    next_num = count + 1
    return f"rp2-avail-{next_num:04d}"

@router.get(
    "/{employee_id}/availability", response_model=List[AvailabilityResponse]
)
def get_employee_availability(
    employee_id: str,
    start_date: Optional[date] = Query(
        None, description="Filter records starting from this date"
    ),
    end_date: Optional[date] = Query(
        None, description="Filter records up to this date"
    ),
    db: Session = Depends(get_db),
):
    """Fetch availability entries with optional date range filtering."""
    query = db.query(Availability).filter(
        Availability.resource_id == employee_id,
        Availability.resource_type == "employee",
    )

    if start_date:
        query = query.filter(
            Availability.week_start_date >= normalize_to_monday(start_date)
        )
    if end_date:
        query = query.filter(
            Availability.week_start_date <= normalize_to_monday(end_date)
        )

    return query.order_by(Availability.week_start_date.asc()).all()


@router.post(
    "/{employee_id}/availability",
    response_model=AvailabilityResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_or_update_availability(
    employee_id: str,
    avail_in: AvailabilityCreate,
    db: Session = Depends(get_db),
):
    """Add or update availability hours for a given week (Fixed ID generation & Monday alignment)."""
    employee = (
        db.query(CompanyEmployee)
        .filter(CompanyEmployee.employee_id == employee_id)
        .first()
    )
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    monday = normalize_to_monday(avail_in.week_start_date)

    existing = (
        db.query(Availability)
        .filter(
            Availability.resource_id == employee_id,
            Availability.week_start_date == monday,
        )
        .first()
    )

    if existing:
        existing.available_hours = (
            0 if avail_in.is_on_leave else avail_in.available_hours
        )
        existing.is_on_leave = avail_in.is_on_leave
        db.commit()
        db.refresh(existing)
        return existing

    # FIX: Generating formatted primary key (e.g. rp2-avail-0001)
    new_avail_id = generate_availability_id(db)

    new_avail = Availability(
        availability_id=new_avail_id,
        resource_id=employee_id,
        resource_type="employee",
        week_start_date=monday,
        available_hours=0 if avail_in.is_on_leave else avail_in.available_hours,
        is_on_leave=avail_in.is_on_leave,
    )
    db.add(new_avail)
    db.commit()
    db.refresh(new_avail)
    return new_avail


# --- NEW API 1: Date Range PTO Leave Submission ---
@router.post("/{employee_id}/leave", status_code=status.HTTP_200_OK)
def submit_date_range_leave(
    employee_id: str,
    payload: DateRangeLeaveRequest,
    db: Session = Depends(get_db),
):
    """Submits multi-week leave, setting matching weeks to 0 available hours and on_leave = True."""
    if payload.end_date < payload.start_date:
        raise HTTPException(
            status_code=400, detail="End date cannot be before start date"
        )

    current_date = payload.start_date
    updated_weeks = []

    while current_date <= payload.end_date:
        monday = normalize_to_monday(current_date)

        existing = (
            db.query(Availability)
            .filter(
                Availability.resource_id == employee_id,
                Availability.week_start_date == monday,
            )
            .first()
        )

        new_avail_id = generate_availability_id(db)
        
        if existing:
            existing.available_hours = 0
            existing.is_on_leave = True
        else:
            new_avail = Availability(
                availability_id=new_avail_id,
                resource_id=employee_id,
                resource_type="employee",
                week_start_date=monday,
                available_hours=0,
                is_on_leave=True,
            )
            db.add(new_avail)

        updated_weeks.append(monday)
        current_date = monday + timedelta(days=7)

    db.commit()
    return {
        "status": "success",
        "message": f"Leave applied across {len(set(updated_weeks))} week(s).",
    }






@router.get("/{employee_id}/daily-bandwidth")
def get_employee_daily_bandwidth(
    employee_id: str,
    db: Session = Depends(get_db)
):
    """
    Calculates today's exact remaining working hours for the current week, 
    accounting for elapsed workdays and active project allocations.
    """
    today = date.today()
    current_monday = normalize_to_monday(today)
    
    # Python weekday: Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6
    day_of_week = today.weekday()
    
    # 1. Fetch Gross Weekly Capacity from Availability table (defaults to 40)
    avail = db.query(Availability).filter(
        Availability.resource_id == employee_id,
        Availability.week_start_date == current_monday
    ).first()

    gross_weekly_hours = avail.available_hours if avail else 40
    is_on_leave = avail.is_on_leave if avail else False

    if is_on_leave:
        return {
            "today": today,
            "status": "On Leave",
            "gross_weekly_hours": 0,
            "elapsed_hours": 0,
            "allocated_hours": 0,
            "remaining_unallocated_hours": 0
        }

    # Standard daily hours (assumes 5 working days per week)
    daily_standard_hours = gross_weekly_hours / 5.0  # e.g., 40 / 5 = 8 hrs/day

    # 2. Calculate Elapsed Hours for past days in current week
    # If it's Monday (0), 0 days elapsed. If Wednesday (2), 2 days elapsed (Mon & Tue = 16 hrs).
    past_workdays = min(day_of_week, 5)  # Cap at 5 for weekends
    elapsed_hours = past_workdays * daily_standard_hours

    # 3. Sum current active allocations for this week
    w_end = current_monday + timedelta(days=6)
    allocated_hours = (
        db.query(func.coalesce(func.sum(Allocation.allocated_hours), 0))
        .join(Project, Allocation.project_id == Project.project_id)
        .filter(
            Allocation.resource_id == employee_id,
            func.lower(Allocation.status).in_(["assigned", "accepted", "proposed", "rejected", "substituted"]),
            Project.start_date <= w_end,
            or_(Project.end_date >= current_monday, Project.end_date.is_(None))
        )
        .scalar()
    )

    # 4. Net Remaining Unallocated Hours for the rest of this week
    # Formula: Gross Capacity - Elapsed Unused Time - Allocated Hours
    remaining_hours = max(0, gross_weekly_hours - elapsed_hours - allocated_hours)

    return {
        "today": today.strftime("%Y-%m-%d"),
        "day_of_week": today.strftime("%A"),
        "gross_weekly_hours": gross_weekly_hours,
        "elapsed_hours_this_week": elapsed_hours,
        "assigned_project_hours": allocated_hours,
        "remaining_unallocated_hours": remaining_hours
    }

@router.get("/{employee_id}/bandwidth", response_model=List[BandwidthForecastItem])
def get_employee_weekly_bandwidth(
    employee_id: str,
    num_weeks: int = Query(default=8, ge=1, le=52),
    db: Session = Depends(get_db)
):
    STANDARD_WEEKLY_GROSS = 40.0  # 8 hrs/day * 5 days

    # Query active project allocations for this employee
    active_allocations = (
        db.query(Allocation)
        .filter(
            Allocation.resource_id == employee_id,
            Allocation.status.in_(["assigned", "accepted", "ASSIGNED", "ACCEPTED"])
        )
        .all()
    ) if 'Allocation' in globals() else []

    # Total allocated hours across assigned projects
    total_allocated = sum(
        getattr(a, "allocated_hours", 32.0) for a in active_allocations
    ) if active_allocations else 0.0

    # Calculate weekly Monday dates starting from the current week
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())

    projections = []
    for week_idx in range(num_weeks):
        week_monday = start_of_week + timedelta(weeks=week_idx)

        # Basic logic (extend with Leave table checks if needed)
        gross = STANDARD_WEEKLY_GROSS
        allocated = min(total_allocated, gross)
        is_leave = False  # Set to True if employee has approved leave this week
        
        net_free = 0.0 if is_leave else max(0.0, gross - allocated)

        projections.append(
            BandwidthForecastItem(
                week_start_date=week_monday.strftime("%b %d, %Y"),  # Generates "Aug 17, 2026"
                gross_available_hours=gross,
                allocated_hours=allocated,
                is_on_leave=is_leave,
                net_free_hours=net_free
            )
        )

    return projections
