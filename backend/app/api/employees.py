# app/api/employees.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.api.deps import get_db
from app.models import CompanyEmployee
from app.schemas import EmployeeResponse, EmployeeCreate

router = APIRouter()

@router.get("/", response_model=List[EmployeeResponse])
def get_employees(
    is_team_lead: Optional[bool] = Query(None, description="Filter employees by team lead status"),
    department: Optional[str] = Query(None, description="Filter by department name"),
    db: Session = Depends(get_db)
):
    """List all employees with optional team lead or department filters."""
    query = db.query(CompanyEmployee)
    
    if is_team_lead is not None:
        query = query.filter(CompanyEmployee.is_team_lead == is_team_lead)
    if department:
        query = query.filter(CompanyEmployee.department.ilike(f"%{department}%"))
        
    return query.all()

@router.post("/", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(employee_in: EmployeeCreate, db: Session = Depends(get_db)):
    """Register a new company employee."""
    existing = db.query(CompanyEmployee).filter(CompanyEmployee.email == employee_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Employee with this email already exists")
    
    employee = CompanyEmployee(**employee_in.model_dump())
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee

@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee_by_id(employee_id: UUID, db: Session = Depends(get_db)):
    """Fetch details of a single employee."""
    employee = db.query(CompanyEmployee).filter(CompanyEmployee.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee