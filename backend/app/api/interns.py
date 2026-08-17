# app/api/interns.py
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.intern import InternsAndStudents, InternSkill
from app.schemas.intern import (
    InternCreate,
    InternResponse,
    InternUpdate,
    InternSkillCreate,
    InternSkillResponse,
)

router = APIRouter()


# ==========================================
# INTERNS & STUDENTS ENDPOINTS
# ==========================================
@router.get("", response_model=List[InternResponse])
def get_interns(db: Session = Depends(get_db)):
    """Fetch all interns/students along with their extracted skills."""
    interns = db.query(InternsAndStudents).all()
    
    for intern in interns:
        intern.skills = (
            db.query(InternSkill)
            .filter(InternSkill.intern_id == intern.intern_id)
            .all()
        )
    return interns


@router.post("", response_model=InternResponse, status_code=status.HTTP_201_CREATED)
def create_intern(intern_in: InternCreate, db: Session = Depends(get_db)):
    """Create a new intern or student entry (optionally with skill mappings)."""
    # Check if email is unique
    existing = db.query(InternsAndStudents).filter(InternsAndStudents.email == intern_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An intern with email '{intern_in.email}' already exists."
        )

    intern_data = intern_in.model_dump(exclude={"skills"})
    new_intern = InternsAndStudents(**intern_data)
    
    db.add(new_intern)
    db.commit()
    db.refresh(new_intern)

    # Attach initial skills if provided in creation request
    created_skills = []
    if intern_in.skills:
        for skill in intern_in.skills:
            db_skill = InternSkill(
                intern_id=new_intern.intern_id,
                **skill.model_dump()
            )
            db.add(db_skill)
            created_skills.append(db_skill)
        
        db.commit()
        for skill in created_skills:
            db.refresh(skill)

    new_intern.skills = created_skills
    return new_intern


@router.get("/{intern_id}", response_model=InternResponse)
def get_intern_by_id(intern_id: str, db: Session = Depends(get_db)):
    """Fetch a single intern by ID."""
    intern = db.query(InternsAndStudents).filter(InternsAndStudents.intern_id == intern_id).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern/Student record not found")

    intern.skills = (
        db.query(InternSkill)
        .filter(InternSkill.intern_id == intern_id)
        .all()
    )
    return intern


@router.patch("/{intern_id}", response_model=InternResponse)
def update_intern(intern_id: str, intern_in: InternUpdate, db: Session = Depends(get_db)):
    """Update intern details, status (AVAILABLE/ASSIGNED), or review status."""
    intern = db.query(InternsAndStudents).filter(InternsAndStudents.intern_id == intern_id).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern/Student record not found")

    update_data = intern_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(intern, field, value)

    db.commit()
    db.refresh(intern)

    intern.skills = (
        db.query(InternSkill)
        .filter(InternSkill.intern_id == intern_id)
        .all()
    )
    return intern


@router.delete("/{intern_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_intern(intern_id: str, db: Session = Depends(get_db)):
    """Delete an intern record."""
    intern = db.query(InternsAndStudents).filter(InternsAndStudents.intern_id == intern_id).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern/Student record not found")

    db.delete(intern)
    db.commit()
    return None


# ==========================================
# INTERN SKILLS ENDPOINTS
# ==========================================
@router.post("/{intern_id}/skills", response_model=InternSkillResponse, status_code=status.HTTP_201_CREATED)
def add_intern_skill(intern_id: str, skill_in: InternSkillCreate, db: Session = Depends(get_db)):
    """Add or link a new skill to an existing intern."""
    intern = db.query(InternsAndStudents).filter(InternsAndStudents.intern_id == intern_id).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern/Student record not found")

    skill_data = skill_in.model_dump(exclude={"intern_id"})
    new_skill = InternSkill(intern_id=intern_id, **skill_data)

    db.add(new_skill)
    db.commit()
    db.refresh(new_skill)
    return new_skill


@router.delete("/{intern_id}/skills/{skill_entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_intern_skill(intern_id: str, skill_entry_id: UUID, db: Session = Depends(get_db)):
    """Remove a skill entry from an intern."""
    skill_entry = db.query(InternSkill).filter(
        InternSkill.id == skill_entry_id,
        InternSkill.intern_id == intern_id
    ).first()

    if not skill_entry:
        raise HTTPException(status_code=404, detail="Intern skill entry not found")

    db.delete(skill_entry)
    db.commit()
    return None