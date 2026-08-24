# app/api/interns.py
from dotenv import load_dotenv
load_dotenv()

import traceback
import uuid
import sys
import io
import inspect
import urllib.request
from pypdf import PdfReader

from importlib import import_module
from pathlib import Path
import logging
from typing import List, Dict, Any
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
from ai_engine.extraction import extract_skills_from_text
from ai_engine.embedding import generate_embedding

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

def get_resume_bytes(url_or_path: str) -> bytes:
    """Fetch file bytes from a public HTTP URL or Supabase storage path."""
    if url_or_path.startswith("http://") or url_or_path.startswith("https://"):
        req = urllib.request.Request(url_or_path, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as response:
            return response.read()
    else:
        clean_path = url_or_path.split("resume/")[-1] if "resume/" in url_or_path else url_or_path
        return download_file_from_supabase(bucket_name="resume", destination_path=clean_path)


def extract_text_from_pdf_bytes(file_bytes: bytes) -> str:
    """Extract plain text from PDF bytes."""
    try:
        pdf_file = io.BytesIO(file_bytes)
        reader = PdfReader(pdf_file)
        text = "".join([page.extract_text() or "" for page in reader.pages])
        return text.strip()
    except Exception as e:
        logger.warning(f"⚠️ Failed to parse PDF text: {e}")
        return ""


# String to Integer mapping for database insertion
TEXT_TO_INT_LEVEL = {
    "BEGINNER": 1,
    "INTERMEDIATE": 3,
    "ADVANCED": 4,
    "EXPERT": 5,
}


def parse_level_to_int(val: Any) -> int:
    """Standardize integer ratings (1-5) or string ratings into database integer values."""
    if isinstance(val, int):
        return max(1, min(5, val))
    if isinstance(val, str):
        if val.isdigit():
            return max(1, min(5, int(val)))
        upper_val = val.upper()
        if upper_val in TEXT_TO_INT_LEVEL:
            return TEXT_TO_INT_LEVEL[upper_val]
    return 3  # Default to Intermediate (3) if unspecified


def get_next_skill_number(db: Session) -> int:
    """Find highest numeric ID matching 'rp2-skl-XXXX' to increment sequentially."""
    last_skill = (
        db.query(Skill.skill_id)
        .filter(Skill.skill_id.like("rp2-skl-%"))
        .order_by(Skill.skill_id.desc())
        .first()
    )
    if last_skill and last_skill[0]:
        try:
            return int(last_skill[0].split("-")[-1])
        except (ValueError, IndexError):
            return 0
    return 0


@router.post("", response_model=InternResponse, status_code=status.HTTP_201_CREATED)
async def create_intern(intern_in: InternCreate, db: Session = Depends(get_db)):
    """
    Create a new intern entry safely. Automatically extracts resume skills,
    maps master skills, links junction tables, and formats output.
    """
    # 1. Unique email check
    existing = db.query(InternsAndStudents).filter(InternsAndStudents.email == intern_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An intern with email '{intern_in.email}' already exists."
        )

    # 2. Extract payload and set defaults
    raw_payload = intern_in.model_dump(exclude={"skills"})

    if raw_payload.get("designation_id") == "":
        raw_payload["designation_id"] = None

    if not raw_payload.get("review_status"):
        raw_payload["review_status"] = "UNVERIFIED"

    if not raw_payload.get("created_at"):
        raw_payload["created_at"] = datetime.now(timezone.utc)

    # 3. Resume Extraction via AI Engine
    extracted_skills_raw: List[Any] = []
    resume_target = (
        raw_payload.get("resume_document_url")
        or raw_payload.get("resume_path")
        or getattr(intern_in, "resume_document_url", None)
        or getattr(intern_in, "resume_path", None)
    )

    print(f"\n🔍 DEBUG: resume_target = '{resume_target}'", flush=True)

    if resume_target:
        try:
            print("⏳ Fetching resume bytes...", flush=True)
            file_bytes = get_resume_bytes(resume_target)
            print(f"✅ Downloaded {len(file_bytes)} bytes", flush=True)

            extracted_text = extract_text_from_pdf_bytes(file_bytes)
            print(f"📄 Extracted PDF Text Length: {len(extracted_text)} characters", flush=True)

            if not extracted_text:
                print("⚠️ WARNING: PDF yielded 0 text characters (File may be an image/scanned PDF).", flush=True)

            input_payload = extracted_text if extracted_text else file_bytes

            if extract_skills_from_text and callable(extract_skills_from_text):
                print("🤖 Invoking AI extract_skills_from_text...", flush=True)
                if inspect.iscoroutinefunction(extract_skills_from_text):
                    extracted_info = await extract_skills_from_text(input_payload)
                else:
                    extracted_info = extract_skills_from_text(input_payload)

                print(f"🤖 Raw AI Output: {extracted_info}", flush=True)

                if isinstance(extracted_info, dict):
                    if not raw_payload.get("university") and extracted_info.get("university"):
                        raw_payload["university"] = extracted_info["university"]
                    extracted_skills_raw = extracted_info.get("skills", [])
                elif isinstance(extracted_info, list):
                    extracted_skills_raw = extracted_info

                print(f"✅ Extracted Skills Count: {len(extracted_skills_raw)}", flush=True)
            else:
                print("❌ ERROR: 'extract_skills_from_text' is None or not callable.", flush=True)

        except Exception as ai_err:
            print(f"❌ Resume Processing Exception: {str(ai_err)}", flush=True)

    try:
        # 4. Filter payload dynamically to matching model columns ONLY
        valid_intern_columns = {col.key for col in InternsAndStudents.__table__.columns}
        filtered_model_data = {k: v for k, v in raw_payload.items() if k in valid_intern_columns}

        new_intern = InternsAndStudents(**filtered_model_data)
        db.add(new_intern)
        db.commit()
        db.refresh(new_intern)

        # 5. Aggregate manual and extracted skills with Integer Level Mapping
        skill_map: Dict[str, Dict[str, Any]] = {}

        # Manual skills from request payload
        if intern_in.skills:
            for s in intern_in.skills:
                s_dict = s.model_dump() if hasattr(s, "model_dump") else dict(s)
                name = (s_dict.get("skill_name") or s_dict.get("name") or "").strip()
                if name:
                    key = name.lower()
                    skill_map[key] = {
                        "skill_name": name,
                        "proficiency_level": parse_level_to_int(s_dict.get("proficiency_level")),
                        "extraction_score": float(s_dict.get("extraction_score", 1.0))
                    }

        # AI-extracted skills with integer level parsing
        for item in extracted_skills_raw:
            if isinstance(item, str):
                name = item.strip()
                level = 3
                score = 0.85
            elif isinstance(item, dict):
                name = (item.get("skill_name") or item.get("name") or "").strip()
                level = parse_level_to_int(item.get("proficiency_level"))
                raw_score = item.get("extraction_score") or item.get("confidence") or item.get("score") or 0.85
                score = float(raw_score)
            else:
                continue

            key = name.lower()
            if key and key not in skill_map:
                skill_map[key] = {
                    "skill_name": name,
                    "proficiency_level": level,
                    "extraction_score": score
                }

        print(f"📊 Processed {len(skill_map)} unique skills to insert.", flush=True)

        # Dynamic column detection for Skill model
        skill_name_col = "skill_name" if hasattr(Skill, "skill_name") else ("name" if hasattr(Skill, "name") else "title")
        skill_attr = getattr(Skill, skill_name_col)

        # Detect valid columns on InternSkill model
        intern_skill_valid_cols = {col.key for col in InternSkill.__table__.columns}

        # Initialize sequential ID counter
        current_skill_num = get_next_skill_number(db)

        # 6. Map/Create Master Skills & Link Junction Rows
        for s_data in skill_map.values():
            skill_name = s_data["skill_name"]

            master_skill = db.query(Skill).filter(skill_attr.ilike(skill_name)).first()

            if not master_skill:
                current_skill_num += 1
                new_skill_id = f"rp2-skl-{current_skill_num:04d}"

                skill_kwargs = {skill_name_col: skill_name}

                if hasattr(Skill, "skill_id"):
                    skill_kwargs["skill_id"] = new_skill_id

                if hasattr(Skill, "skill_embedding"):
                    if generate_embedding and callable(generate_embedding):
                        try:
                            skill_kwargs["skill_embedding"] = generate_embedding(skill_name)
                        except Exception as emb_err:
                            logger.warning(f"⚠️ Failed embedding for '{skill_name}': {emb_err}")

                master_skill = Skill(**skill_kwargs)
                db.add(master_skill)
                db.flush()

            # Map confidence / score field variations alongside integer proficiency level
            junction_data = {
                "intern_id": new_intern.intern_id,
                "skill_id": master_skill.skill_id,
                "proficiency_level": s_data["proficiency_level"],
                "extraction_score": s_data["extraction_score"],
                "extraction_confidence": s_data["extraction_score"],
                "confidence": s_data["extraction_score"],
                "score": s_data["extraction_score"],
            }
            filtered_junction_data = {k: v for k, v in junction_data.items() if k in intern_skill_valid_cols}

            db_intern_skill = InternSkill(**filtered_junction_data)
            db.add(db_intern_skill)

        db.commit()

        # 7. Query joined skills explicitly to build response payload
        joined_skills = (
            db.query(InternSkill, skill_attr.label("skill_name"))
            .join(Skill, InternSkill.skill_id == Skill.skill_id)
            .filter(InternSkill.intern_id == new_intern.intern_id)
            .all()
        )

        formatted_skills = [
            {
                "intern_id": row.InternSkill.intern_id,
                "skill_id": row.InternSkill.skill_id,
                "skill_name": row.skill_name,
                "proficiency_level": getattr(row.InternSkill, "proficiency_level", 3),
                "extraction_score": getattr(
                    row.InternSkill,
                    "extraction_confidence",
                    getattr(
                        row.InternSkill,
                        "extraction_score",
                        getattr(row.InternSkill, "confidence", 0.85)
                    )
                ),
            }
            for row in joined_skills
        ]

        response_data = {
            col.key: getattr(new_intern, col.key)
            for col in new_intern.__table__.columns
        }
        response_data["skills"] = formatted_skills

        return response_data

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