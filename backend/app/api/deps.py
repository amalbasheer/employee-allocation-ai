# app/api/deps.py
from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.core.supabase import supabase
from app.schemas.project import UserProfile

security = HTTPBearer()

def get_db() -> Generator[Session, None, None]:
    """Yields a database session per request and closes it automatically."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserProfile:
    """Verifies Bearer token with Supabase and builds current UserProfile."""
    token = credentials.credentials
    try:
        user_res = supabase.auth.get_user(token)
        if not user_res or not user_res.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )

        user_id = user_res.user.id
        email = user_res.user.email

        # 1. Search company_employees table
        emp_query = supabase.table("company_employees").select("*").eq("email", email).execute()
        if emp_query.data and len(emp_query.data) > 0:
            emp_data = emp_query.data[0]
            role = emp_data.get("role") or user_res.user.user_metadata.get("role") or "employee"
            name = emp_data.get("name") or emp_data.get("full_name") or email.split("@")[0]
            return UserProfile(id=user_id, email=email, role=role, name=name)

        # 2. Search interns_and_students table
        intern_query = supabase.table("interns_and_students").select("*").eq("email", email).execute()
        if intern_query.data and len(intern_query.data) > 0:
            intern_data = intern_query.data[0]
            name = intern_data.get("name") or intern_data.get("full_name") or email.split("@")[0]
            return UserProfile(id=user_id, email=email, role="student", name=name)

        # 3. Fallback
        role = user_res.user.user_metadata.get("role", "employee")
        return UserProfile(id=user_id, email=email, role=role, name=email.split("@")[0])

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication error: {str(e)}"
        )

def require_admin(current_user: UserProfile = Depends(get_current_user)) -> UserProfile:
    """Restricts operation strictly to Admin users."""
    if current_user.role.lower() not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required."
        )
    return current_user