# app/api/auth.py
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from app.core.supabase import supabase

router = APIRouter()

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserProfile(BaseModel):
    id: str
    email: str
    role: str
    name: str | None = None

class LoginResponse(BaseModel):
    token: str
    user: UserProfile

@router.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    try:
        # 1. Authenticate credentials via Supabase Auth (auth.users)
        auth_res = supabase.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password
        })

        if not auth_res.user or not auth_res.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid email or password"
            )

        email = auth_res.user.email
        user_id = auth_res.user.id

        # 2. Check 'employees' table first
        emp_query = supabase.table("company_employees").select("*").eq("email", email).execute()
        
        if emp_query.data and len(emp_query.data) > 0:
            emp_data = emp_query.data[0]
            # Determine if admin or regular employee
            role = emp_data.get("role") or auth_res.user.user_metadata.get("role") or "employee"
            name = emp_data.get("name") or emp_data.get("full_name") or email.split("@")[0]

            return LoginResponse(
                token=auth_res.session.access_token,
                user=UserProfile(
                    id=user_id,
                    email=email,
                    role=role,
                    name=name
                )
            )

        # 3. Check 'interns' table if not found in employees
        intern_query = supabase.table("interns_and_students").select("*").eq("email", email).execute()

        if intern_query.data and len(intern_query.data) > 0:
            intern_data = intern_query.data[0]
            role = "student"
            name = intern_data.get("name") or intern_data.get("full_name") or email.split("@")[0]

            return LoginResponse(
                token=auth_res.session.access_token,
                user=UserProfile(
                    id=user_id,
                    email=email,
                    role=role,
                    name=name
                )
            )

        # 4. Fallback if user is in Auth but not yet indexed in profile tables
        role = auth_res.user.user_metadata.get("role", "employee")
        return LoginResponse(
            token=auth_res.session.access_token,
            user=UserProfile(
                id=user_id,
                email=email,
                role=role,
                name=email.split("@")[0]
            )
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )