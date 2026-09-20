"""
db.py
All the raw database reads live here — one place, so if TM renames a
column later, you only fix it in this file.
"""

import os
import json
from dotenv import load_dotenv
from datetime import date
from typing import Optional, Dict, List, Tuple, Set
from sqlalchemy import create_engine, text, Engine
from ai_engine.project_taxonomy import get_required_roles

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise EnvironmentError("DATABASE_URL not set in .env")

engine = create_engine(DATABASE_URL, pool_size=20,         # Increase base connections from 5 to 20
    max_overflow=20,      # Allow up to 20 additional burst connections
    pool_timeout=5,       # Raise an error after 5s instead of hanging for 30s
    pool_pre_ping=True,)

CATEGORY_TO_DEPARTMENT = {
    "Machine Learning": "Data Science",
    "Data Science": "Data Science",
    "Data Analytics": "Data Analytics",
}

def category_to_department(category: str) -> str | None:
    """Maps a project's subject category to the department used for
    mentor/intern filtering. Returns None for unmapped categories,
    so recommendations fall back to showing everyone rather than
    coming back empty."""
    return CATEGORY_TO_DEPARTMENT.get(category)

def _parse_embedding(val):
    """
    Normalizes an embedding value into a real Python list, regardless
    of whether it comes back from Postgres as a string representation
    or an actual list/array.
    """
    if val is None:
        return None
    if isinstance(val, str):
        return json.loads(val)
    return list(val)


def get_project(project_id: str) -> dict:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM projects WHERE project_id = :pid"),
            {"pid": project_id},
        ).mappings().fetchone()
    return dict(row) if row else None


def get_project_requirements(project_id: str) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT pr.skill_id, pr.min_proficiency, pr.is_mandatory,
                       s.skill_name, pr.requirement_embedding
                FROM project_requirements pr
                JOIN skills s ON pr.skill_id = s.skill_id
                WHERE pr.project_id = :pid
            """),
            {"pid": project_id},
        ).mappings().fetchall()
    return [
        {
            "skill_id": r["skill_id"],
            "embedding": _parse_embedding(r["requirement_embedding"]),
            "min_proficiency": r["min_proficiency"],
            "is_mandatory": r["is_mandatory"],
        }
        for r in rows
    ]


def get_available_mentors(domain: str = None, region: str = None, check_project_conflicts: bool = True) -> list[dict]:
    """
    Excludes anyone with an active PROJECT allocation, unless
    check_project_conflicts=False. Optionally filters by department
    and/or location.
    """
    query = """
    SELECT employee_id AS id, name, weekly_capacity_hours, is_team_lead, location, preferred_audience
    FROM company_employees
    """
    conditions = []
    params = {}

    if check_project_conflicts:
        conditions.append("""
            NOT EXISTS (
                SELECT 1 FROM allocations a
                WHERE a.resource_id = employee_id
                AND a.status IN ('proposed', 'assigned')
                AND a.reference_type = 'project'
            )
        """)
    if domain:
        conditions.append("department = :domain")
        params["domain"] = domain
    if region:
        conditions.append("location LIKE :region")
        params["region"] = f"%{region}%"

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    with engine.connect() as conn:
        rows = conn.execute(text(query), params).mappings().fetchall()
    return [dict(r) for r in rows]

def get_available_interns(domain: str = None) -> list[dict]:
    """
    Available means: current_status = 'AVAILABLE', verified, not already
    tied to an active allocation. No longer using a hardcoded time window
    — admin will manage TERMINATED status directly instead.
    """
    query = """
        SELECT intern_id AS id, name, role, current_status
        FROM interns_and_students i
        WHERE current_status = 'AVAILABLE'
          AND review_status = 'verified'
          AND NOT EXISTS (
              SELECT 1 FROM allocations a
              WHERE a.resource_id = i.intern_id
              AND a.status IN ('proposed', 'assigned')
          )
    """
    params = {}
    if domain:
        query += " AND department = :domain"
        params["domain"] = domain

    with engine.connect() as conn:
        rows = conn.execute(text(query), params).mappings().fetchall()
    return [dict(r) for r in rows]


def get_person_skills(person_id: str, person_type: str) -> list[dict]:
    table = "employee_skills" if person_type == "employee" else "intern_skills"
    id_column = "employee_id" if person_type == "employee" else "intern_id"

    with engine.connect() as conn:
        rows = conn.execute(
            text(f"""
                SELECT ps.skill_id, ps.proficiency_level, s.skill_embedding
                FROM {table} ps
                JOIN skills s ON ps.skill_id = s.skill_id
                WHERE ps.{id_column} = :pid
            """),
            {"pid": person_id},
        ).mappings().fetchall()

    return [
        {
            "skill_id": r["skill_id"],
            "embedding": _parse_embedding(r["skill_embedding"]),
            "proficiency_level": r["proficiency_level"],
        }
        for r in rows
    ]

# Candidate slot patterns for 2-day and 3-day technical domains
SLOTS_2_DAY = [
    ("morning", ["Tuesday", "Thursday"]),
    ("evening", ["Tuesday", "Thursday"]),
    ("morning", ["Monday", "Wednesday"]),
    ("evening", ["Monday", "Wednesday"]),
]

SLOTS_3_DAY = [
    ("morning", ["Monday", "Wednesday", "Friday"]),
    ("evening", ["Monday", "Wednesday", "Friday"]),
]


def _parse_days(day_data) -> List[str]:
    """Helper to parse day_of_week regardless of whether it's stored as JSON, list, or CSV string."""
    if not day_data:
        return []
    if isinstance(day_data, list):
        return [d.strip().capitalize() for d in day_data]
    if isinstance(day_data, str):
        try:
            parsed = json.loads(day_data)
            if isinstance(parsed, list):
                return [d.strip().capitalize() for d in parsed]
        except Exception:
            pass
        return [d.strip().capitalize() for d in day_data.split(",")]
    return []


def get_softskill_rotated_slot(sub_domain: str, month_num: int) -> Tuple[str, List[str]]:
    """
    Calculates rotated Softskill slot based on month and target sub-domain (DA/DS):
    - June (6): DS -> Mon Morning, DA -> Mon Evening
    - July (7): DA -> Tue Morning, DS -> Tue Evening
    - Aug  (8): DS -> Wed Morning, DA -> Wed Evening
    All Softskill batches also include 'Friday' for the Friday Morning Common Session.
    """
    rotated_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Saturday"]
    
    # Select day based on month rotation (June = index 0)
    day_name = rotated_days[(month_num - 6) % len(rotated_days)]

    # Flips morning/evening assignment between DA and DS every month
    is_even_month = (month_num % 2 == 0)
    if "DS" in sub_domain or "Data Science" in sub_domain:
        session = "morning" if is_even_month else "evening"
    else:  # DA / Data Analytics
        session = "evening" if is_even_month else "morning"

    # Always includes Friday Morning for the shared Common Session
    return session, [day_name, "Friday"]


def get_mentor_busy_slots(conn, mentor_id: int, start_dt: date, end_dt: date) -> Set[Tuple[str, str]]:
    """
    Fetches all (session, day_name) pairs where the mentor is occupied 
    in overlapping date ranges across BOTH student_batches and projects.
    """
    busy_slots: Set[Tuple[str, str]] = set()

    # 1. Check overlapping student_batches
    batch_rows = conn.execute(
        text("""
            SELECT session, day_of_week
            FROM student_batches
            WHERE mentor_id = :mentor_id
              AND start_date <= :end_dt
              AND end_date >= :start_dt
              AND status != 'cancelled'
        """),
        {"mentor_id": mentor_id, "start_dt": start_dt, "end_dt": end_dt}
    ).mappings().fetchall()

    for row in batch_rows:
        sess = (row["session"] or "").lower()
        days = _parse_days(row["day_of_week"])
        if sess:
            for day in days:
                # Exclude Friday Morning as it is the shared Common Session
                if not (sess == "morning" and day == "Friday"):
                    busy_slots.add((sess, day))

    # 2. Check overlapping projects
    project_rows = conn.execute(
        text("""
            SELECT p.session, p.day_of_week
            FROM projects p
            JOIN allocations a ON p.project_id = a.reference_id
            WHERE a.resource_id = :mentor_id
              AND p.start_date <= :end_dt
              AND p.end_date >= :start_dt
        """),
        {"mentor_id": mentor_id, "start_dt": start_dt, "end_dt": end_dt}
    ).mappings().fetchall()

    for row in project_rows:
        sess = (row["session"] or "").lower()
        days = _parse_days(row["day_of_week"])
        if sess:
            for day in days:
                if not (sess == "morning" and day == "Friday"):
                    busy_slots.add((sess, day))

    return busy_slots


def find_free_slot_for_mentor(
    conn, mentor_id: int, domain: str, start_dt: date, end_dt: date, sub_domain: str = "Data Science"
) -> Optional[Tuple[str, List[str]]]:
    """
    Finds the first available (session, day_list) slot for a mentor based on domain requirements.
    """
    busy_slots = get_mentor_busy_slots(conn, mentor_id, start_dt, end_dt)

    # Softskill logic: Rotated month day + Common Friday
    if domain == "Softskill":
        session, days = get_softskill_rotated_slot(sub_domain, start_dt.month)
        rotated_day = days[0]  # Check conflict only for the individual rotated day
        if (session.lower(), rotated_day) not in busy_slots:
            return session, days
        return None

    # Candidate slots for standard domains (Bridge, DA, DS, Agentic AI)
    candidate_slots = SLOTS_3_DAY if domain == "Agentic AI" else SLOTS_2_DAY

    for session, days in candidate_slots:
        has_conflict = any((session.lower(), day) in busy_slots for day in days)
        if not has_conflict:
            return session, days

    return None


def get_next_mentor_for_batch(
    domain: str, 
    month_num: int, 
    year: int = 2026, 
    sub_domain: str = "Data Science", 
    engine: Engine = None
) -> Optional[dict]:
    """
    Finds or assigns the next mentor for a batch, including session and day_of_week.
    
    1. Agentic AI maps to 'Data Science' department.
    2. Softskill maps strictly to 'Softskill' department.
    3. Bridge allows mentors from ANY department.
    4. Data Analytics / Data Science map to their respective departments.
    """
    # 1. Department Filter Rule
    if domain == "Agentic AI":
        dept_clause = "ce.department = 'Data Science'"
        params = {}
    elif domain == "Softskill":
        dept_clause = "ce.department = 'Soft Skill'"
        params = {}
    elif domain == "Bridge":
        dept_clause = "1=1"  # Mentors can come from ANY department
        params = {}
    else:
        dept_clause = "ce.department = :dept"
        params = {"dept": domain}

    # 2. Calculate 2-Month Block Range
    block_start_month = month_num if month_num % 2 == 0 else month_num - 1
    block_end_month = block_start_month + 1

    # 3. Calculate Batch Start & End Dates for Overlap Checks (4-month duration)
    start_dt = date(year, month_num, 15)
    end_month = month_num + 4
    end_year = year
    if end_month > 12:
        end_month -= 12
        end_year += 1
    end_dt = date(end_year, end_month, 14)

    with engine.connect() as conn:
        # --- RULE A: Reuse Mentor in Same 2-Month Block ---
        existing = conn.execute(
            text(f"""
                SELECT sb.mentor_id, ce.name, sb.session, sb.day_of_week
                FROM student_batches sb
                JOIN company_employees ce ON ce.employee_id = sb.mentor_id
                WHERE sb.domain = :domain
                  AND sb.mentor_id IS NOT NULL
                  AND EXTRACT(MONTH FROM sb.start_date) BETWEEN :block_start AND :block_end
                  AND EXTRACT(YEAR FROM sb.start_date) = :year
                LIMIT 1
            """),
            {
                "domain": domain, 
                "block_start": block_start_month, 
                "block_end": block_end_month, 
                "year": year
            },
        ).mappings().fetchone()

        if existing:
            mentor_id = existing["mentor_id"]
            existing_days = _parse_days(existing["day_of_week"])
            existing_session = existing["session"]

            if existing_session and existing_days:
                return {
                    "employee_id": mentor_id,
                    "name": existing["name"],
                    "session": existing_session,
                    "day_of_week": existing_days
                }
            
            slot = find_free_slot_for_mentor(conn, mentor_id, domain, start_dt, end_dt, sub_domain)
            if slot:
                return {
                    "employee_id": mentor_id,
                    "name": existing["name"],
                    "session": slot[0],
                    "day_of_week": slot[1]
                }

        # --- RULE B: Round-Robin Selection (Fairness + Availability) ---
        candidates = conn.execute(
            text(f"""
                SELECT ce.employee_id, ce.name, COUNT(sb.batch_id) AS batch_count
                FROM company_employees ce
                LEFT JOIN student_batches sb ON sb.mentor_id = ce.employee_id
                WHERE {dept_clause}
                GROUP BY ce.employee_id, ce.name
                ORDER BY batch_count ASC, ce.employee_id ASC
            """),
            params,
        ).mappings().fetchall()

        for candidate in candidates:
            m_id = candidate["employee_id"]
            slot = find_free_slot_for_mentor(conn, m_id, domain, start_dt, end_dt, sub_domain)
            if slot:
                return {
                    "employee_id": m_id,
                    "name": candidate["name"],
                    "session": slot[0],
                    "day_of_week": slot[1],
                    "batch_count": candidate["batch_count"]
                }

    return None


def recommend_batch_replacement(batch_id: str) -> list[dict]:
    """
    For a batch whose mentor is leaving mid-cycle — returns ALL eligible
    mentors (any mentor, not just team leads) in the batch's domain,
    ranked by fewest CURRENT batch assignments first (round-robin order),
    excluding whoever's currently assigned. Counts directly from
    student_batches.mentor_id — batches don't use the allocations table.
    """
    with engine.connect() as conn:
        batch = conn.execute(
            text("SELECT * FROM student_batches WHERE batch_id = :bid"),
            {"bid": batch_id},
        ).mappings().fetchone()
        if not batch:
            raise ValueError(f"No batch found with id {batch_id}")

        rows = conn.execute(
            text("""
                SELECT ce.employee_id AS id, ce.name, ce.is_team_lead,
                       COUNT(sb.batch_id) AS batch_count
                FROM company_employees ce
                LEFT JOIN student_batches sb ON sb.mentor_id = ce.employee_id
                WHERE ce.department = :domain AND ce.employee_id != :current_mentor
                GROUP BY ce.employee_id, ce.name, ce.is_team_lead
                ORDER BY batch_count ASC, ce.employee_id ASC
            """),
            {"domain": batch["domain"], "current_mentor": batch.get("mentor_id") or ""},
        ).mappings().fetchall()
    return [dict(r) for r in rows]

def get_batch(batch_id: str) -> dict:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM student_batches WHERE batch_id = :bid"),
            {"bid": batch_id},
        ).mappings().fetchone()
    if not row:
        return None
    result = dict(row)
    for key in ("start_date", "end_date", "created_at"):
        if result.get(key) is not None:
            result[key] = str(result[key])
    return result


def get_training_engagement(engagement_id: str) -> dict:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM training_engagements WHERE engagement_id = :eid"),
            {"eid": engagement_id},
        ).mappings().fetchone()
    if not row:
        return None
    result = dict(row)
    # Convert date objects to strings so Gemini's function-calling can serialize them
    for key in ("start_date", "end_date", "created_at"):
        if result.get(key) is not None:
            result[key] = str(result[key])
    return result


def get_allocation_target(allocation: dict) -> dict:
    """
    Given an allocation row, fetches the actual project/batch/training
    engagement it points to — dispatches based on reference_type since
    reference_id alone doesn't tell you which table to check.
    """
    ref_type = allocation.get("reference_type")
    ref_id = allocation.get("reference_id")

    if ref_type == "project":
        return get_project(ref_id)
    elif ref_type == "batch":
        return get_batch(ref_id)
    elif ref_type == "training":
        return get_training_engagement(ref_id)
    else:
        raise ValueError(f"Unknown reference_type: {ref_type}")

def search_project_by_title(title_keyword: str) -> list[dict]:
    """Finds projects whose title contains the given keyword — lets the
    chatbot resolve a project name into its actual project_id."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT project_id, title, project_type, status
                FROM projects
                WHERE title ILIKE :keyword
            """),
            {"keyword": f"%{title_keyword}%"},
        ).mappings().fetchall()
    return [dict(r) for r in rows]


def get_intern_details(intern_id: str) -> dict:
    """Full details for one intern, including basic profile info."""
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT intern_id, name, email, college_institution, degree_program,
                       current_status, department, review_status
                FROM interns_and_students WHERE intern_id = :id
            """),
            {"id": intern_id},
        ).mappings().fetchone()
    return dict(row) if row else None


def get_employee_details(employee_id: str) -> dict:
    """Full details for one employee, including basic profile info."""
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT employee_id, name, email, department, designation_id,
                       weekly_capacity_hours, is_team_lead
                FROM company_employees WHERE employee_id = :id
            """),
            {"id": employee_id},
        ).mappings().fetchone()
    return dict(row) if row else None

def search_training_by_title(title_keyword: str) -> list[dict]:
    """Finds training engagements whose title contains the given keyword —
    lets the chatbot resolve a training name into its actual engagement_id."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT engagement_id, title, engagement_type, status
                FROM training_engagements
                WHERE title ILIKE :keyword
            """),
            {"keyword": f"%{title_keyword}%"},
        ).mappings().fetchall()
    return [dict(r) for r in rows]

def get_best_mentor_for_domain(domain: str) -> list[dict]:
    """
    General 'who's the best mentor for X domain' — no specific project
    to score against, so this ranks team leads first (more senior/capable
    role), then by available capacity as a tiebreaker.
    """
    mentors = get_available_mentors(domain=domain)
    return sorted(
        mentors,
        key=lambda m: (not m.get("is_team_lead", False), -m.get("weekly_capacity_hours", 0))
    )[:5]

def get_workload_extremes(domain: str = None) -> dict:
    """
    Returns the least busy and most busy mentors based on their current
    active commitments across projects, trainings and batches.

    Useful for questions like:
    - Who is the least busy mentor?
    - Who is the most busy mentor?
    """

    query = """
        SELECT
            ce.employee_id,
            ce.name,
            ce.department,
            ce.is_team_lead,
            COUNT(a.allocation_id) AS active_commitments
        FROM company_employees ce
        LEFT JOIN allocations a
            ON a.resource_id = ce.employee_id
            AND a.status IN ('proposed', 'assigned')
        WHERE 1=1
    """

    params = {}

    if domain:
        query += " AND ce.department = :domain"
        params["domain"] = domain

    query += """
        GROUP BY ce.employee_id,
                 ce.name,
                 ce.department,
                 ce.is_team_lead
        ORDER BY active_commitments ASC, ce.name
    """

    with engine.connect() as conn:
        mentors = conn.execute(text(query), params).mappings().fetchall()

    mentors = [dict(m) for m in mentors]

    if not mentors:
        return {
            "least_busy": [],
            "most_busy": []
        }

    min_count = mentors[0]["active_commitments"]
    max_count = mentors[-1]["active_commitments"]

    least_busy = [
        m for m in mentors
        if m["active_commitments"] == min_count
    ]

    most_busy = [
        m for m in mentors
        if m["active_commitments"] == max_count
    ]

    return {
        "least_busy": least_busy,
        "most_busy": most_busy
    }

def get_employee_workload_summary(employee_name: str) -> dict:
    """
    Returns a complete summary of one employee's active work across
    projects, trainings and student batches.
    """

    with engine.connect() as conn:

        employee = conn.execute(
            text("""
                SELECT employee_id,
                       name,
                       department,
                       weekly_capacity_hours,
                       is_team_lead
                FROM company_employees
                WHERE LOWER(name)=LOWER(:name)
            """),
            {"name": employee_name},
        ).mappings().fetchone()

        if not employee:
            return None

        employee_id = employee["employee_id"]

        allocations = conn.execute(
            text("""
                SELECT
                    reference_type,
                    reference_id,
                    status
                FROM allocations
                WHERE resource_id=:id
                AND status IN ('proposed','assigned','accepted')
            """),
            {"id": employee_id},
        ).mappings().fetchall()

    projects = []
    trainings = []
    batches = []

    for allocation in allocations:

        if allocation["reference_type"] == "project":
            project = get_project(allocation["reference_id"])
            if project:
                projects.append(project["title"])

        elif allocation["reference_type"] == "training":
            training = get_training_engagement(allocation["reference_id"])
            if training:
                trainings.append(training["title"])

        elif allocation["reference_type"] == "batch":
            batch = get_batch(allocation["reference_id"])
            if batch:
                batches.append(batch["batch_name"])

    return {
        "employee": employee["name"],
        "department": employee["department"],
        "team_lead": employee["is_team_lead"],
        "weekly_capacity_hours": employee["weekly_capacity_hours"],
        "projects": projects,
        "trainings": trainings,
        "batches": batches,
        "project_count": len(projects),
        "training_count": len(trainings),
        "batch_count": len(batches)
    }

def get_project_assignments(project_id: str) -> list[dict]:
    """Who is currently assigned (proposed/accepted/assigned) to a project."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT a.resource_id, a.resource_type, a.status, a.role_on_project,
                       COALESCE(ce.name, i.name) AS name
                FROM allocations a
                LEFT JOIN company_employees ce ON ce.employee_id = a.resource_id
                LEFT JOIN interns_and_students i ON i.intern_id = a.resource_id
                WHERE a.reference_type = 'project' AND a.reference_id = :pid
                  AND a.status IN ('proposed', 'accepted', 'assigned')
            """),
            {"pid": project_id},
        ).mappings().fetchall()
    return [dict(r) for r in rows]

def get_mentor_availability_for_week(week_start_date: str) -> list[dict]:
    """Who's free for a specific week (YYYY-MM-DD, must be a Monday),
    based on the availability table's recorded hours and leave status."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT ce.employee_id, ce.name,
                       COALESCE(av.available_hours, ce.weekly_capacity_hours) AS available_hours,
                       COALESCE(av.is_on_leave, FALSE) AS is_on_leave
                FROM company_employees ce
                LEFT JOIN availability av
                    ON av.resource_id = ce.employee_id
                    AND av.resource_type = 'employee'
                    AND av.week_start_date = :week
                WHERE COALESCE(av.is_on_leave, FALSE) = FALSE
                  AND COALESCE(av.available_hours, ce.weekly_capacity_hours) > 0
            """),
            {"week": week_start_date},
        ).mappings().fetchall()
    return [dict(r) for r in rows]

def get_available_mentors_for_training(domain: str = None, region: str = None) -> list[dict]:
    """
    Specifically for training/workshop availability questions — always
    ignores project commitments, since project and training availability
    are tracked independently. Use this instead of get_available_mentors
    for ANY training-related question.
    """
    return get_available_mentors(domain=domain, region=region, check_project_conflicts=False)

def check_hypothetical_training_availability(domain: str, region: str, audience: str) -> dict:
    """
    THE ONLY function to use when checking mentor availability for a
    training that does NOT exist yet in the system (a new/hypothetical
    workshop instance). Takes domain, region, and audience — ALL THREE
    are required — and returns a ranked list of eligible team leads,
    correctly ignoring project commitments, correctly filtering by
    domain and region, and flagging audience match/mismatch.

    Args:
        domain: "Data Analytics" or "Data Science" (full name, required)
        region: the region name, e.g. "Kochi" (required)
        audience: e.g. "college_students", "school_students", or "professionals" (required)

    Returns:
        {"available_mentors": [...], "count": N} — always this exact shape,
        even if count is 0. Each mentor includes an "audience_match" field.
    """
    mentors = get_available_mentors(domain=domain, region=region, check_project_conflicts=False)
    team_leads = [m for m in mentors if m.get("is_team_lead")]

    for tl in team_leads:
        candidate_audience = tl.get("preferred_audience")
        if candidate_audience:
            candidate_list = [a.strip().lower() for a in candidate_audience.split(",")]
            tl["audience_match"] = audience.strip().lower() in candidate_list
        else:
            tl["audience_match"] = False

    return {"available_mentors": team_leads, "count": len(team_leads)}

def check_project_readiness(project_id: str) -> dict:
    """Checks readiness AND names who's assigned to each role, or flags what's missing."""
    assignments = get_project_assignments(project_id)
    roles_needed = get_required_roles(get_project(project_id)["project_type"])

    assigned_employees = [a["name"] for a in assignments if a["resource_type"] == "employee"]
    assigned_interns = [a["name"] for a in assignments if a["resource_type"] == "intern"]

    missing_roles = []
    if "team_lead" in roles_needed and not assigned_employees:
        missing_roles.append("team_lead")
    if "intern" in roles_needed and not assigned_interns:
        missing_roles.append("intern")

    return {
        "ready": len(missing_roles) == 0,
        "missing_roles": missing_roles,
        "assigned_team_lead": assigned_employees[0] if assigned_employees else None,
        "assigned_interns": assigned_interns,
    }

def get_all_mentors_with_project_count(domain: str = None) -> list[dict]:
    """
    Returns ALL mentors in the domain (no hard exclusion), each with
    their current active project count — used for workload-penalized
    project recommendations, so genuinely busy people are still shown,
    just appropriately penalized rather than invisible.
    """
    query = """
        SELECT ce.employee_id AS id, ce.name, ce.weekly_capacity_hours, ce.is_team_lead,
               COUNT(a.allocation_id) AS active_project_count
        FROM company_employees ce
        LEFT JOIN allocations a ON a.resource_id = ce.employee_id
            AND a.reference_type = 'project' AND a.status IN ('proposed', 'assigned')
        WHERE 1=1
    """
    params = {}
    if domain:
        query += " AND ce.department = :domain"
        params["domain"] = domain
    query += " GROUP BY ce.employee_id, ce.name, ce.weekly_capacity_hours, ce.is_team_lead"

    with engine.connect() as conn:
        rows = conn.execute(text(query), params).mappings().fetchall()
    return [dict(r) for r in rows]

def get_employee_by_name(name: str) -> dict:
    """Looks up an employee's full record by name (case-insensitive)."""
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM company_employees WHERE LOWER(name) = LOWER(:name)"),
            {"name": name},
        ).mappings().fetchone()
    return dict(row) if row else None

def search_batch_by_title(name_keyword: str) -> list[dict]:
    """Finds student batches whose name contains the given keyword —
    lets the chatbot resolve a batch name/description into real records."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT sb.batch_id, sb.batch_name, sb.domain, sb.mentor_id, sb.status,
                       ce.name AS mentor_name
                FROM student_batches sb
                LEFT JOIN company_employees ce ON ce.employee_id = sb.mentor_id
                WHERE sb.batch_name ILIKE :keyword
            """),
            {"keyword": f"%{name_keyword}%"},
        ).mappings().fetchall()
    return [dict(r) for r in rows]

def suggest_training_date(preferred_month: int, preferred_year: int = 2026, avoid_conflicts_domain: str = None) -> dict:
    """
    Finds ALL available weekday dates for a new training in the given
    month — skips Sundays, avoids conflicts with existing trainings,
    never suggests a past date. Returns every valid option at once,
    so follow-up questions ("any other dates?") can be answered directly
    from the conversation history without needing to call this again.
    """
    from datetime import date, timedelta

    with engine.connect() as conn:
        query = """
            SELECT start_date, end_date FROM training_engagements
            WHERE EXTRACT(MONTH FROM start_date) = :month
            AND EXTRACT(YEAR FROM start_date) = :year
        """
        params = {"month": preferred_month, "year": preferred_year}
        if avoid_conflicts_domain:
            query += " AND domain = :domain"
            params["domain"] = avoid_conflicts_domain

        existing_dates = conn.execute(text(query), params).fetchall()

    busy_dates = set()
    for start, end in existing_dates:
        if start and end:
            current = start
            while current <= end:
                busy_dates.add(current)
                current += timedelta(days=1)

    today = date.today()
    first_day = date(preferred_year, preferred_month, 1)
    search_start = max(first_day, today + timedelta(days=1))

    next_month = preferred_month + 1 if preferred_month < 12 else 1
    next_year = preferred_year if preferred_month < 12 else preferred_year + 1
    last_day = date(next_year, next_month, 1) - timedelta(days=1)

    all_available = []
    current = search_start
    while current <= last_day:
        if current.weekday() != 6 and current not in busy_dates:
            all_available.append(str(current))
        current += timedelta(days=1)

    return {
        "all_available_dates": all_available,
        "top_recommendation": all_available[0] if all_available else None,
        "reason": f"{len(all_available)} available weekday(s) found in this month, from tomorrow onward."
    }

def get_bulk_person_skills(person_ids: list[str], person_type: str) -> dict[str, list[dict]]:
    if not person_ids:
        return {}
    
    table = "employee_skills" if person_type == "employee" else "intern_skills"
    id_column = "employee_id" if person_type == "employee" else "intern_id"

    with engine.connect() as conn:
        rows = conn.execute(
            text(f"""
                SELECT es.{id_column} AS person_id, s.skill_id, s.skill_name, 
                       es.proficiency_level, s.skill_embedding
                FROM {table} es
                JOIN skills s ON s.skill_id = es.skill_id
                WHERE es.{id_column} = ANY(:ids)
            """),
            {"ids": person_ids},
        ).mappings().fetchall()

    result = {pid: [] for pid in person_ids}
    for row in rows:
        result[row["person_id"]].append({
            "skill_id": row["skill_id"],
            "skill_name": row["skill_name"],
            "proficiency_level": row["proficiency_level"],
            "embedding": _parse_embedding(row["skill_embedding"]),
        })
    return result