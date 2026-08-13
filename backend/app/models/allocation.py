# backend/app/models/allocation.py
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Allocation(Base):
    __tablename__ = "allocations"

    allocation_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    resource_type: Mapped[str] = mapped_column(String(20), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.project_id"))
    role_on_project: Mapped[str] = mapped_column(String(50), default="lead_mentor")
    allocated_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    suitability_score: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="proposed")
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    assigned_by: Mapped[str] = mapped_column(String(50), default="AI_Engine")

class Substitution(Base):
    __tablename__ = "substitutions"

    substitution_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    original_allocation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("allocations.allocation_id"))
    substitute_resource_type: Mapped[str] = mapped_column(String(20), nullable=False)
    substitute_resource_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class AllocationLog(Base):
    __tablename__ = "allocation_logs"

    log_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    allocation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("allocations.allocation_id"))
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    changed_by: Mapped[str] = mapped_column(String(100), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)