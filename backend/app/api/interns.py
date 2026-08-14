# app/api/interns.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.api.deps import get_db
from app.models import InternsAndStudents
from app.schemas import InternResponse, InternCreate
from app.utils.supabase_client import upload_file_to_supabase

router = APIRouter()

@router.get("/", response_model=List[InternResponse])
def get_interns_and_students(
    role: Optional[str] = Query(None, description="Filter by role: 'intern' or 'student'"),
    review_status: Optional[str] = Query(None, description="Filter by status e.g. 'pending_review'"),
    db: Session = Depends(get_db)
):
    """List all candidates with optional role filtering."""
    query = db.query(InternsAndStudents)
    
    if role:
        query = query.filter(InternsAndStudents.role == role.lower())
    if review_status:
        query = query.filter(InternsAndStudents.review_status == review_status)
        
    return query.all()

@router.post("/by-link", response_model=InternResponse, status_code=status.HTTP_201_CREATED)
def create_intern_with_url(candidate_in: InternCreate, db: Session = Depends(get_db)):
    """Create candidate entry using a Google Drive or external URL link."""
    existing = db.query(InternsAndStudents).filter(InternsAndStudents.email == candidate_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Candidate with this email already exists")
    
    candidate = InternsAndStudents(**candidate_in.model_dump())
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate

@router.post("/upload-resume", response_model=InternResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume_file(
    name: str = Form(...),
    email: str = Form(...),
    college_institution: str = Form(...),
    degree_program: Optional[str] = Form(None),
    role: str = Form("intern"),
    weekly_capacity_hours: int = Form(20),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a physical resume file (.pdf/.docx) to Supabase Storage and create candidate entry."""
    existing = db.query(InternsAndStudents).filter(InternsAndStudents.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Candidate with this email already exists")

    # Upload to Supabase Bucket 'resumes'
    file_bytes = await file.read()
    file_url = upload_file_to_supabase(
        file_bytes=file_bytes,
        filename=file.filename,
        content_type=file.content_type
    )

    candidate = InternsAndStudents(
        name=name,
        email=email,
        college_institution=college_institution,
        degree_program=degree_program,
        role=role,
        weekly_capacity_hours=weekly_capacity_hours,
        resume_document_url=file_url
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate