# app/api/employees.py
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.employee import CompanyEmployee, EmployeeSkill, Availability
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
    # Unique email check
    existing = db.query(CompanyEmployee).filter(CompanyEmployee.email == employee_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An employee with email '{employee_in.email}' already exists."
        )

    emp_data = employee_in.model_dump(exclude={"skills"})
    new_employee = CompanyEmployee(**emp_data)
    
    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)

    # Process nested skills if provided during creation
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


@router.get("/{employee_id}", response_model=CompanyEmployeeResponse)
def get_employee_by_id(employee_id: UUID, db: Session = Depends(get_db)):
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
def update_employee(employee_id: UUID, employee_in: CompanyEmployeeUpdate, db: Session = Depends(get_db)):
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
def delete_employee(employee_id: UUID, db: Session = Depends(get_db)):
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
def add_employee_skill(employee_id: UUID, skill_in: EmployeeSkillCreate, db: Session = Depends(get_db)):
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
def remove_employee_skill(employee_id: UUID, skill_id: UUID, db: Session = Depends(get_db)):
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
@router.get("/{employee_id}/availability", response_model=List[AvailabilityResponse])
def get_employee_availability(employee_id: UUID, db: Session = Depends(get_db)):
    """Fetch availability entries for a specific employee."""
    return (
        db.query(Availability)
        .filter(
            Availability.resource_id == employee_id,
            Availability.resource_type == "employee"
        )
        .all()
    )


@router.post("/{employee_id}/availability", response_model=AvailabilityResponse, status_code=status.HTTP_201_CREATED)
def add_or_update_availability(employee_id: UUID, avail_in: AvailabilityCreate, db: Session = Depends(get_db)):
    """Add or update availability hours for a given week."""
    employee = db.query(CompanyEmployee).filter(CompanyEmployee.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Upsert logic handling unique constraint on (resource_id, week_start_date)
    existing = db.query(Availability).filter(
        Availability.resource_id == employee_id,
        Availability.week_start_date == avail_in.week_start_date
    ).first()

    if existing:
        existing.available_hours = avail_in.available_hours
        existing.is_on_leave = avail_in.is_on_leave
        db.commit()
        db.refresh(existing)
        return existing

    new_avail = Availability(
        resource_id=employee_id,
        resource_type="employee",
        week_start_date=avail_in.week_start_date,
        available_hours=avail_in.available_hours,
        is_on_leave=avail_in.is_on_leave
    )
    db.add(new_avail)
    db.commit()
    db.refresh(new_avail)
    return new_avail