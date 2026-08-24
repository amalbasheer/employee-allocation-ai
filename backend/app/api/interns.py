# app/api/interns.py
import traceback
import uuid
import sys
from pathlib import Path
import logging
from typing import List
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import TypeAdapter
from sqlalchemy.exc import IntegrityError

# Import your AI engine extractor and helper utilities
ROOT_DIR = Path(__file__).resolve().parents[3]  # Adjust depth based on app location
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

# Import AI Engine services with resilient fallbacks
try:
    from ai_engine.extraction import extract_skills_from_text
except ImportError:
    extract_skills_from_text = None

try:
    from ai_engine.embedding import generate_embedding
except ImportError:
    generate_embedding = None

logger = logging.getLogger(__name__)


from app.utils.supabase_client import download_file_from_supabase  # helper to fetch file bytes

from app.database import get_db
from app.api.deps import require_admin  # Auth dependency
from app.schemas.project import UserProfile
from app.utils.supabase_client import upload_file_to_supabase, supabase_client
from app.models.intern import InternsAndStudents, InternSkill
from app.models.taxonomy import Skill
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
    try:
        interns = db.query(InternsAndStudents).all()
        for intern in interns:
            intern.skills = (
                db.query(InternSkill)
                .filter(InternSkill.intern_id == intern.intern_id)
                .all()
            )
        return interns
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail={"error_type": type(e).__name__, "message": str(e), "trace": traceback.format_exc()}
        )

@router.post("", response_model=InternResponse, status_code=status.HTTP_201_CREATED)
async def create_intern(intern_in: InternCreate, db: Session = Depends(get_db)):
    """
    Create a new intern entry, extract skills via AI Engine,
    map or create them in the master `skills` table (with embeddings),
    and store `skill_id` and `extraction_score` in the `intern_skills` table.
    """
    
    # 1. Unique email check
    existing = db.query(InternsAndStudents).filter(InternsAndStudents.email == intern_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An intern with email '{intern_in.email}' already exists."
        )

    # 2. Extract payload and sanitize values
    intern_data = intern_in.model_dump(exclude={"skills"})

    if intern_data.get("designation_id") == "":
        intern_data["designation_id"] = None

    if not intern_data.get("review_status"):
        intern_data["review_status"] = "UNVERIFIED"

    if not intern_data.get("created_at"):
        intern_data["created_at"] = datetime.now(timezone.utc)

    # 3. AI Extraction & Skill Aggregation from Resume
    extracted_skills_data = []
    if intern_in.resume_document_url:
        try:
            # Clean path if a full URL or prefix was provided
            path = intern_in.resume_document_url
            clean_path = path.split("resume/")[-1] if "resume/" in path else path

            # Download file bytes from Supabase storage bucket
            file_bytes = download_file_from_supabase(
                bucket_name="resume", 
                destination_path=clean_path
            )
            
            # Pass file bytes to your AI extractor module
            extracted_info = await extract_skills_from_text(file_bytes)
            
            if isinstance(extracted_info, dict):
                if not intern_data.get("university") and extracted_info.get("university"):
                    intern_data["university"] = extracted_info["university"]
                extracted_skills_data = extracted_info.get("skills", [])
        except Exception as ai_err:
            print(f"Warning: Failed to extract resume details: {ai_err}")

    try:
        # 4. Save new intern record
        new_intern = InternsAndStudents(**intern_data)
        db.add(new_intern)
        db.commit()
        db.refresh(new_intern)

        # 5. Process and aggregate skills (Manual + AI Extracted)
        skill_map = {}

        # Add explicitly provided manual skills first (default score = 1.0)
        if intern_in.skills:
            for s in intern_in.skills:
                s_dict = s.model_dump()
                skill_name = s_dict["skill_name"].strip()
                key = skill_name.lower()
                skill_map[key] = {
                    "skill_name": skill_name,
                    "proficiency_level": s_dict.get("proficiency_level", "INTERMEDIATE"),
                    "extraction_score": float(s_dict.get("extraction_score", 1.0))
                }

        # Merge extracted skills from AI Engine (handles strings or dicts)
        for item in extracted_skills_data:
            if isinstance(item, str):
                name = item.strip()
                level = "INTERMEDIATE"
                score = 0.85
            elif isinstance(item, dict):
                name = item.get("skill_name", "").strip()
                level = item.get("proficiency_level", "INTERMEDIATE")
                score = float(item.get("extraction_score", item.get("score", 0.85)))
            else:
                continue

            key = name.lower()
            if key and key not in skill_map:
                skill_map[key] = {
                    "skill_name": name,
                    "proficiency_level": level,
                    "extraction_score": score
                }

        # 6. Resolve/Create master Skill records and save to intern_skills junction table
        created_intern_skills = []
        for s_data in skill_map.values():
            skill_name = s_data["skill_name"]

            # Check if master skill already exists in the master `skills` table
            master_skill = db.query(Skill).filter(Skill.skill_name.ilike(skill_name)).first()

            if not master_skill:
                # Generate skill embedding vector via AI Engine only if master skill doesn't exist yet
                embedding_vector = generate_embedding(skill_name)

                master_skill = Skill(
                    skill_name=skill_name,
                    skill_embedding=embedding_vector
                )
                db.add(master_skill)
                db.flush() # Populates master_skill.skill_id safely before committing

            # Create association in intern_skills table linking intern_id -> skill_id
            db_intern_skill = InternSkill(
                intern_id=new_intern.intern_id,
                skill_id=master_skill.skill_id,
                proficiency_level=s_data["proficiency_level"],
                extraction_score=s_data["extraction_score"]
            )
            db.add(db_intern_skill)
            created_intern_skills.append(db_intern_skill)

        if created_intern_skills:
            db.commit()
            for skill in created_intern_skills:
                db.refresh(skill)

        new_intern.skills = created_intern_skills
        return new_intern

    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database integrity error: {str(e.orig)}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create intern: {str(e)}"
        )


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


@router.patch("/{intern_id}/verify", response_model=InternResponse)
def verify_intern(
    intern_id: str,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_admin),
):
    """Verify an intern record and automatically track the approving admin."""
    intern = db.query(InternsAndStudents).filter(InternsAndStudents.intern_id == intern_id).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern/Student record not found")

    intern.review_status = "VERIFIED"
    intern.reviewed_by = current_user.name or current_user.email

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

# ==========================================
# UPLOAD RESUME ENDPOINTS
# ==========================================

ALLOWED_MIME_TYPES = [
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
]

@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    # 1. Validate file extension / MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF and DOC/DOCX files are allowed."
        )

    # 2. Generate a unique file path to prevent overwriting existing files
    file_extension = file.filename.split(".")[-1] if "." in file.filename else "pdf"
    destination_path = f"intern_resumes/{uuid.uuid4()}.{file_extension}"

    try:
        # 3. Read file content as bytes
        file_bytes = await file.read()

        # 4. Upload to Supabase bucket
        bucket_name = "resume"  # Make sure this bucket exists in your Supabase storage
        upload_response = upload_file_to_supabase(
            file=file_bytes,
            bucket_name=bucket_name,
            destination_path=destination_path
        )

        # 5. Generate the Public URL (if your Supabase bucket is public)
        file_url = None
        if supabase_client:
            file_url = supabase_client.storage.from_(bucket_name).get_public_url(destination_path)

        return {
            "message": "Resume uploaded successfully",
            "file_path": destination_path,
            "file_url": file_url
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload resume: {str(e)}"
        )