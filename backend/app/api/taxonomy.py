# app/api/taxonomy.py
import traceback

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.api.deps import get_db
from app.models import Skill, Designation
from app.schemas import SkillResponse, SkillCreate, DesignationResponse, DesignationCreate

router = APIRouter()

# --- SKILLS ENDPOINTS ---
@router.get("/skills", response_model=List[SkillResponse])
def get_skills(db: Session = Depends(get_db)):
    return db.query(Skill).all()

@router.post("/skills", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
def create_skill(skill_in: SkillCreate, db: Session = Depends(get_db)):
    """Add a new master skill."""
    existing = db.query(Skill).filter(Skill.skill_name == skill_in.skill_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Skill name already exists")
    
    skill = Skill(**skill_in.model_dump())
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill

# --- DESIGNATIONS ENDPOINTS ---
@router.get("/designations", response_model=List[DesignationResponse])
def get_designations(db: Session = Depends(get_db)):
    """Fetch all master designations."""
    return db.query(Designation).all()

@router.post("/designations", response_model=DesignationResponse, status_code=status.HTTP_201_CREATED)
def create_designation(designation_in: DesignationCreate, db: Session = Depends(get_db)):
    """Add a new master designation."""
    existing = db.query(Designation).filter(Designation.title == designation_in.title).first()
    if existing:
        raise HTTPException(status_code=400, detail="Designation title already exists")
    
    designation = Designation(**designation_in.model_dump())
    db.add(designation)
    db.commit()
    db.refresh(designation)
    return designation