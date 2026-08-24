# backend/models/webinar.py

from datetime import date, datetime
from typing import Optional
from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    Date,
    DateTime,
    Text,
    ForeignKey,
    CheckConstraint,
    text,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

# Adjust this import based on your base model setup (e.g., from ..database import Base)
from app.database import Base


class TrainingEngagement(Base):
    """
    Table 1: Webinars, Demos, Workshops, Seminars (Skill-matched, Mentor-only)
    """
    __tablename__ = "training_engagements"

    engagement_id = Column(String(20), primary_key=True, server_default=text("('rp2-train-' || lpad(nextval('training_id_seq')::text, 4, '0'))"),)
    title = Column(String(150), nullable=False)
    engagement_type = Column(String(30), nullable=False)  # 'webinar' | 'demo' | 'workshop' | 'seminar'
    description = Column(Text, nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    required_hours = Column(Integer, nullable=False, server_default=text("2"))
    mentor_id = Column(String(20), ForeignKey("company_employees.employee_id"), nullable=True,)
    status = Column(String(20), nullable=False, server_default=text("'open'"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(),)

    __table_args__ = (CheckConstraint(r"engagement_id ~ '^rp2-train-\d{4}$'", name="check_engagement_id_format",),)

    # Relationships
    mentor = relationship("CompanyEmployee", backref="training_engagements")
    requirements = relationship("TrainingRequirement", back_populates="engagement", cascade="all, delete-orphan",)
    allocations = relationship("Allocation", primaryjoin="and_("
                "TrainingEngagement.engagement_id == foreign(Allocation.reference_id), "
                "Allocation.reference_type.in_(['webinar', 'training', 'engagement'])"
                ")", back_populates="webinar", overlaps="allocations,project,batch")
    
class TrainingRequirement(Base):
    """
    Skill requirements for training engagements (Handles pgvector skill matching)
    """
    __tablename__ = "training_requirements"

    requirement_id = Column(String(20), primary_key=True, server_default=text("('rp2-treq-' || lpad(nextval('training_id_seq')::text, 4, '0'))"),)
    engagement_id = Column(String(20), ForeignKey("training_engagements.engagement_id", ondelete="CASCADE"), nullable=False,)
    skill_id = Column(String(20), ForeignKey("skills.skill_id", ondelete="CASCADE"), nullable=False,)
    min_proficiency = Column(Integer, nullable=False, server_default=text("1"))
    is_mandatory = Column(Boolean, nullable=False, server_default=text("TRUE"))
    requirement_embedding = Column(Vector(768), nullable=True)

    # Relationships
    engagement = relationship("TrainingEngagement", back_populates="requirements")
    skill = relationship("Skill")


class StudentBatch(Base):
    """
    Table 2: Student Batches (Round-robin assigned, NO skill requirements table)
    """
    __tablename__ = "student_batches"

    batch_id = Column(String(20), primary_key=True, server_default=text("('rp2-batch-' || lpad(nextval('batch_id_seq')::text, 4, '0'))"),)
    batch_name = Column(String(100), nullable=False)
    domain = Column(String(50), nullable=False)  # 'Data Analytics' | 'Data Science'
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    mentor_id = Column(String(20), ForeignKey("company_employees.employee_id"), nullable=True,)
    status = Column(String(20), nullable=False, server_default=text("'open'"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(),)
    delivery_mode = Column(String(20), nullable=True)

    __table_args__ = (CheckConstraint(r"batch_id ~ '^rp2-batch-\d{4}$'", name="check_batch_id_format",),)

    # Relationships
    mentor = relationship("CompanyEmployee", backref="student_batches")
    allocations = relationship("Allocation", primaryjoin="and_("
                "StudentBatch.batch_id == foreign(Allocation.reference_id), "
                "Allocation.reference_type.in_(['batch', 'student_batch', 'studentbatch'])"
                ")", back_populates="batch", overlaps="allocations,webinar,project")