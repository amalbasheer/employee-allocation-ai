# app/api/taxonomy.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.models.taxonomy import Skill, Designation, DesignationSkill
from app.schemas.taxonomy import (
    SkillCreate,
    SkillResponse,
    SkillUpdate,
    DesignationCreate,
    DesignationResponse,
    DesignationUpdate,
    DesignationSkillCreate,
    DesignationSkillResponse,
)

router = APIRouter()


# ==========================================
# SKILLS ENDPOINTS
# ==========================================
@router.get("/skills", response_model=List[SkillResponse])
def get_skills(db: Session = Depends(get_db)):
    """Fetch all skills."""
    return db.query(Skill).all()


@router.post("/skills", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
def create_skill(skill_in: SkillCreate, db: Session = Depends(get_db)):
    """Create a new skill."""
    existing_skill = db.query(Skill).filter(Skill.name == skill_in.name).first()
    if existing_skill:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Skill '{skill_in.name}' already exists."
        )
    
    new_skill = Skill(**skill_in.model_dump())
    db.add(new_skill)
    db.commit()
    db.refresh(new_skill)
    return new_skill


@router.get("/skills/{skill_id}", response_model=SkillResponse)
def get_skill_by_id(skill_id: UUID, db: Session = Depends(get_db)):
    """Fetch a single skill by UUID."""
    skill = db.query(Skill).filter(Skill.skill_id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


# ==========================================
# DESIGNATIONS ENDPOINTS
# ==========================================
@router.get("/designations", response_model=List[DesignationResponse])
def get_designations(db: Session = Depends(get_db)):
    """Fetch all designations."""
    return db.query(Designation).all()


@router.post("/designations", response_model=DesignationResponse, status_code=status.HTTP_201_CREATED)
def create_designation(designation_in: DesignationCreate, db: Session = Depends(get_db)):
    """Create a new designation."""
    existing = db.query(Designation).filter(Designation.title == designation_in.title).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Designation title '{designation_in.title}' already exists."
        )
    
    new_designation = Designation(**designation_in.model_dump())
    db.add(new_designation)
    db.commit()
    db.refresh(new_designation)
    return new_designation


# ==========================================
# DESIGNATION-SKILLS MAPPING ENDPOINTS
# ==========================================
@router.get("/designation-skills", response_model=List[DesignationSkillResponse])
def get_designation_skills(db: Session = Depends(get_db)):
    """Fetch all designation skill mappings."""
    return db.query(DesignationSkill).all()


@router.post("/designation-skills", response_model=DesignationSkillResponse, status_code=status.HTTP_201_CREATED)
def link_skill_to_designation(link_in: DesignationSkillCreate, db: Session = Depends(get_db)):
    """Link a skill to a designation using composite primary keys."""
    # Check if designation exists
    designation = db.query(Designation).filter(Designation.designation_id == link_in.designation_id).first()
    if not designation:
        raise HTTPException(status_code=404, detail="Designation not found")
    
    # Check if skill exists
    skill = db.query(Skill).filter(Skill.skill_id == link_in.skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    # Check if mapping already exists
    existing = db.query(DesignationSkill).filter(
        DesignationSkill.designation_id == link_in.designation_id,
        DesignationSkill.skill_id == link_in.skill_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This skill is already linked to the designation."
        )

    new_mapping = DesignationSkill(**link_in.model_dump())
    db.add(new_mapping)
    db.commit()
    db.refresh(new_mapping)
    return new_mapping


@router.delete("/designation-skills/{designation_id}/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_skill_from_designation(designation_id: UUID, skill_id: UUID, db: Session = Depends(get_db)):
    """Remove a skill link from a designation using composite keys."""
    mapping = db.query(DesignationSkill).filter(
        DesignationSkill.designation_id == designation_id,
        DesignationSkill.skill_id == skill_id
    ).first()

    if not mapping:
        raise HTTPException(status_code=404, detail="Designation-Skill link not found")

    db.delete(mapping)
    db.commit()
    return None