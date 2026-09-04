from datetime import datetime, timedelta, date
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, status
from sqlalchemy import func, extract, desc, case
from sqlalchemy.orm import Session

# Database setup
from app.database import get_db

# All database models matching your schema
from app.models import (
    Allocation,
    Substitution,
    AllocationLog,
    CompanyEmployee,
    EmployeeSkill,
    Availability,
    InternsAndStudents,
    InternSkill,
    Project,
    ProjectRequirement,
    Skill,
    Designation,
    TrainingEngagement,
    TrainingRequirement,
    StudentBatch,
)

router = APIRouter()


@router.get("/overview", status_code=status.HTTP_200_OK)
def get_dashboard_overview(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Consolidated Dashboard API fetching live metrics from all database schema tables.
    """
    now = datetime.utcnow()

    # -------------------------------------------------------------------------
    # 1. TOP-LEVEL KPI METRICS
    # -------------------------------------------------------------------------
    total_projects = db.query(func.count(Project.project_id)).scalar() or 0
    active_projects = (
        db.query(func.count(Project.project_id))
        .filter(func.lower(Project.status).in_(["active", "in progress", "open"]))
        .scalar() or 0
    )

    total_employees = db.query(func.count(CompanyEmployee.employee_id)).scalar() or 0
    total_interns = db.query(func.count(InternsAndStudents.intern_id)).scalar() or 0
    
    pending_intern_reviews = (
        db.query(func.count(InternsAndStudents.intern_id))
        .filter(InternsAndStudents.review_status == "pending_review")
        .scalar() or 0
    )

    # Hours & Resource Utilization
    total_allocated_hours = (
        db.query(func.coalesce(func.sum(Allocation.allocated_hours), 0))
        .filter(func.lower(Allocation.status) == "assigned")
        .scalar() or 0
    )
    
    total_capacity_hours = (
        db.query(func.coalesce(func.sum(CompanyEmployee.weekly_capacity_hours), 0))
        .scalar() or 0
    )

    utilization_rate = (
        round((total_allocated_hours / total_capacity_hours) * 100, 1)
        if total_capacity_hours > 0
        else 0.0
    )

    # AI Match Score Average & Substitutions
    raw_avg_suitability = (
        db.query(func.coalesce(func.avg(Allocation.suitability_score), 0.0))
        .filter(func.lower(Allocation.status) == "assigned")
        .scalar() or 0.0
    )
    avg_ai_match_score = (
        round(raw_avg_suitability * 100, 1)
        if raw_avg_suitability <= 1.0
        else round(raw_avg_suitability, 1)
    )

    total_substitutions = db.query(func.count(Substitution.substitution_id)).scalar() or 0

    # -------------------------------------------------------------------------
    # 2. ALLOCATION TRENDS (LAST 6 MONTHS)
    # -------------------------------------------------------------------------
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    categories = []
    month_keys = []

    for i in range(5, -1, -1):
        year = now.year
        month = now.month - i
        while month <= 0:
            month += 12
            year -= 1
        categories.append(month_names[month - 1])
        month_keys.append((year, month))

    start_date = datetime(month_keys[0][0], month_keys[0][1], 1)

    trend_results = (
        db.query(
            extract("year", Allocation.assigned_at).label("year"),
            extract("month", Allocation.assigned_at).label("month"),
            func.lower(Allocation.status).label("status"),
            func.coalesce(func.sum(Allocation.allocated_hours), 0).label("total_hours"),
        )
        .filter(Allocation.assigned_at >= start_date)
        .group_by("year", "month", func.lower(Allocation.status))
        .all()
    )

    trend_map = {
        (int(row.year), int(row.month), str(row.status)): int(row.total_hours)
        for row in trend_results
    }

    assigned_hours_series = [trend_map.get((yr, mth, "assigned"), 0) for yr, mth in month_keys]
    proposed_hours_series = [trend_map.get((yr, mth, "proposed"), 0) for yr, mth in month_keys]

    # -------------------------------------------------------------------------
    # 3. WORKLOAD ALLOCATION BY ENTITY TYPE (Project vs Webinar vs Batch)
    # -------------------------------------------------------------------------
    entity_allocations = (
        db.query(
            Allocation.reference_type,
            func.coalesce(func.sum(Allocation.allocated_hours), 0).label("hours")
        )
        .filter(func.lower(Allocation.status) == "assigned")
        .group_by(Allocation.reference_type)
        .all()
    )

    type_mapping = {"project": "Projects", "webinar": "Webinars", "training": "Webinars", "batch": "Student Batches"}
    entity_breakdown = {"Projects": 0, "Webinars": 0, "Student Batches": 0}
    
    for row in entity_allocations:
        ref_type = str(row.reference_type).lower()
        key = type_mapping.get(ref_type, "Projects")
        entity_breakdown[key] += int(row.hours)

    # -------------------------------------------------------------------------
    # 4. PROJECT STATUS BREAKDOWN
    # -------------------------------------------------------------------------
    project_status_counts = (
        db.query(Project.status, func.count(Project.project_id).label("count"))
        .group_by(Project.status)
        .all()
    )
    status_dict = {row.status: row.count for row in project_status_counts}
    
    default_statuses = ["In Progress", "Open", "Completed", "Cancelled"]
    for s in status_dict.keys():
        if s not in default_statuses:
            default_statuses.append(s)

    project_status_labels = default_statuses
    project_status_series = [status_dict.get(st, 0) for st in project_status_labels]

    # -------------------------------------------------------------------------
    # 5. TOP SKILLS DEMAND VS SUPPLY COVERAGE
    # -------------------------------------------------------------------------
    top_demanded_skills = (
        db.query(
            Skill.skill_id,
            Skill.skill_name,
            func.count(ProjectRequirement.requirement_id).label("demand_count")
        )
        .join(ProjectRequirement, Skill.skill_id == ProjectRequirement.skill_id)
        .group_by(Skill.skill_id, Skill.skill_name)
        .order_by(desc("demand_count"))
        .limit(5)
        .all()
    )

    skill_coverage_list = []
    for skill_id, skill_name, demand_count in top_demanded_skills:
        emp_supply = db.query(func.count(EmployeeSkill.employee_id)).filter(EmployeeSkill.skill_id == skill_id).scalar() or 0
        intern_supply = db.query(func.count(InternSkill.intern_id)).filter(InternSkill.skill_id == skill_id).scalar() or 0
        total_supply = emp_supply + intern_supply
        
        coverage_pct = round((total_supply / demand_count) * 100, 1) if demand_count > 0 else 100.0
        skill_coverage_list.append({
            "skill_name": skill_name,
            "demand": demand_count,
            "supply": total_supply,
            "coverage_pct": min(coverage_pct, 100.0)
        })

    # -------------------------------------------------------------------------
    # 6. RECENT AUDIT LOGS FEED
    # -------------------------------------------------------------------------
    recent_logs = (
        db.query(
            AllocationLog.log_id,
            AllocationLog.action,
            AllocationLog.changed_by,
            AllocationLog.timestamp,
            Allocation.reference_type,
            Allocation.role_on_project
        )
        .join(Allocation, AllocationLog.allocation_id == Allocation.allocation_id)
        .order_by(desc(AllocationLog.timestamp))
        .limit(6)
        .all()
    )

    logs_feed = [
        {
            "id": log.log_id,
            "action": log.action,
            "changed_by": log.changed_by,
            "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M"),
            "target": f"{log.reference_type.title()} ({log.role_on_project})"
        }
        for log in recent_logs
    ]

    # -------------------------------------------------------------------------
    # 7. WEEKLY AVAILABLE EMPLOYEES
    # -------------------------------------------------------------------------
    availability_records = (
        db.query(Availability, CompanyEmployee)
        .join(
            CompanyEmployee,
            Availability.resource_id == CompanyEmployee.employee_id
        )
        .order_by(desc(Availability.week_start_date))
        .all()
    )

    weekly_available_employees = [
        {
            "availability_id": avail.availability_id,
            "resource_type": avail.resource_type,
            "resource_id": avail.resource_id,
            "employee_name": getattr(emp, "name", getattr(emp, "employee_name", getattr(emp, "full_name", "N/A"))),
            "department": getattr(emp, "department", "N/A"),
            "week_start_date": (
                avail.week_start_date.strftime("%Y-%m-%d")
                if hasattr(avail.week_start_date, "strftime")
                else str(avail.week_start_date)
            ),
            "available_hour": getattr(avail, "available_hour", getattr(avail, "available_hours", 0)),
            "is_on_leave": avail.is_on_leave,
        }
        for avail, emp in availability_records
    ]

    # -------------------------------------------------------------------------
    # COMBINED RESPONSE
    # -------------------------------------------------------------------------
    return {
        "kpis": {
            "total_projects": total_projects,
            "active_projects": active_projects,
            "total_employees": total_employees,
            "total_interns": total_interns,
            "pending_intern_reviews": pending_intern_reviews,
            "allocated_hours": total_allocated_hours,
            "capacity_hours": total_capacity_hours,
            "utilization_rate": utilization_rate,
            "avg_ai_match_score": avg_ai_match_score,
            "total_substitutions": total_substitutions,
        },
        "allocations_trend": {
            "categories": categories,
            "series": [
                {"name": "Assigned Hours", "data": assigned_hours_series},
                {"name": "Proposed Hours", "data": proposed_hours_series},
            ],
        },
        "entity_allocation_breakdown": {
            "labels": list(entity_breakdown.keys()),
            "series": list(entity_breakdown.values()),
        },
        "project_status": {
            "labels": project_status_labels,
            "series": project_status_series,
        },
        "skill_coverage": skill_coverage_list,
        "recent_logs": logs_feed,
        "weekly_available_employees": weekly_available_employees,
    }