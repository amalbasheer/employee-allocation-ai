# app/models/allocation.py
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Float, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.enums import AllocationStatus
from app.models.project import Project

class Allocation(Base):
    __tablename__ = "allocations"

    allocation_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    resource_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "employee" or "student"
    resource_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.project_id"), nullable=False)
    role_on_project: Mapped[str] = mapped_column(String(50), default="lead_mentor")
    allocated_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    suitability_score: Mapped[float] = mapped_column(Float, nullable=False)
    
    status: Mapped[AllocationStatus] = mapped_column(
        SQLEnum(AllocationStatus, name="allocation_status_enum", native_enum=False),
        default=AllocationStatus.PROPOSED,
        nullable=False
    )
    
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    assigned_by: Mapped[str] = mapped_column(String(100), default="AI_Engine")

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="allocations")
    substitutions: Mapped[List["Substitution"]] = relationship("Substitution", back_populates="original_allocation")
    logs: Mapped[List["AllocationLog"]] = relationship("AllocationLog", back_populates="allocation", cascade="all, delete-orphan")


class Substitution(Base):
    __tablename__ = "substitutions"

    substitution_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    original_allocation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("allocations.allocation_id"), nullable=False)
    substitute_resource_type: Mapped[str] = mapped_column(String(20), nullable=False)
    substitute_resource_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship
    original_allocation: Mapped["Allocation"] = relationship("Allocation", back_populates="substitutions")


class AllocationLog(Base):
    __tablename__ = "allocation_logs"

    log_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    allocation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("allocations.allocation_id"), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    changed_by: Mapped[str] = mapped_column(String(100), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship
    allocation: Mapped["Allocation"] = relationship("Allocation", back_populates="logs")