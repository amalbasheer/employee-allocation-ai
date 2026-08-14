# app/api/designation_skills.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.api.deps import get_db
from app.models import DesignationSkill
from app.schemas.designation_skill import DesignationSkillResponse, DesignationSkillCreate

router = APIRouter()

@router.get("/designation/{designation_id}", response_model=List[DesignationSkillResponse])
def get_skills_for_designation(designation_id: UUID, db: Session = Depends(get_db)):
    """Fetch all skills tied to a specific designation."""
    return db.query(DesignationSkill).filter(DesignationSkill.designation_id == designation_id).all()

@router.post("/", response_model=DesignationSkillResponse, status_code=status.HTTP_201_CREATED)
def map_skill_to_designation(mapping_in: DesignationSkillCreate, db: Session = Depends(get_db)):
    """Associate a skill requirement with a designation."""
    mapping = DesignationSkill(**mapping_in.model_dump())
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping

@router.delete("/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_skill_from_designation(mapping_id: UUID, db: Session = Depends(get_db)):
    """Remove a skill from a designation."""
    mapping = db.query(DesignationSkill).filter(DesignationSkill.id == mapping_id).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    db.delete(mapping)
    db.commit()
    return None