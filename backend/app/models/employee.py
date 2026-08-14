from sqlalchemy import String, Float, Integer, Boolean, Column, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class CompanyEmployee(Base):
    __tablename__ = "company_employees"

    employee_id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    designation_id: Mapped[str] = mapped_column(ForeignKey("designations.designation_id"), nullable=True)
    department: Mapped[str] = mapped_column(String(50), nullable=False)
    experience_years: Mapped[float] = mapped_column(Float, default=0.0)
    weekly_capacity_hours: Mapped[int] = mapped_column(Integer, default=40)
    
    # 🆕 NEW COLUMN
    is_team_lead: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)