from sqlalchemy import String, Integer, JSON, Column
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class InternsAndStudents(Base):
    __tablename__ = "interns_and_students"

    intern_id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    college_institution: Mapped[str] = mapped_column(String(150), nullable=False)
    degree_program: Mapped[str] = mapped_column(String(100), nullable=True)
    resume_document_url: Mapped[str] = mapped_column(String, nullable=False)
    
    # 🆕 NEW COLUMN ('intern' or 'student')
    role: Mapped[str] = mapped_column(String(20), default="intern", nullable=False)
    
    review_status: Mapped[str] = mapped_column(String(20), default="pending_review")
    weekly_capacity_hours: Mapped[int] = mapped_column(Integer, default=20)