from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from sqlalchemy.orm import Session

# Database and Supabase Imports (adjust paths as per your project)
from app.api.deps import get_db
from app.core.supabase import supabase


# Router definition
router = APIRouter()


# --- Schemas ---

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserProfile(BaseModel):
    id: str
    email: str
    role: str
    name: Optional[str] = None

class LoginResponse(BaseModel):
    token: str
    user: UserProfile

class ActivateAccountSchema(BaseModel):
    token: str
    password: str


# --- Routes ---

@router.post("/login", response_model=LoginResponse)
def login(credentials: LoginRequest):
    print(f"\n--- [LOGIN ATTEMPT] Email: {credentials.email} ---")
    
    try:
        # 1. Authenticate credentials via Supabase Auth
        print("--> Step 1: Calling supabase.auth.sign_in_with_password...")
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

        # 2. Check 'companyemployees' table first
        print(f"--> Step 2: Querying companyemployees table for {email}...")
        emp_query = supabase.table("company_employees").select("*").eq("email", email).execute()
        
        if emp_query.data and len(emp_query.data) > 0:
            emp_data = emp_query.data[0]
            role = auth_res.user.user_metadata.get("role") or "employee"
            name = emp_data.get("name") or emp_data.get("full_name") or email.split("@")[0]
            profile_id = str(emp_data.get("employee_id") or user_id)

            return LoginResponse(
                token=auth_res.session.access_token,
                user=UserProfile(
                    id=profile_id,
                    email=email,
                    role=role,
                    name=name
                )
            )

        # 3. Check 'interns_and_students' table if not found in employees
        print(f"--> Step 3: Querying interns_and_students table for {email}...")
        intern_query = supabase.table("interns_and_students").select("*").eq("email", email).execute()

        if intern_query.data and len(intern_query.data) > 0:
            intern_data = intern_query.data[0]
            role = "student"
            name = intern_data.get("name") or intern_data.get("full_name") or email.split("@")[0]
            profile_id = str(intern_data.get("intern_id") or user_id)

            return LoginResponse(
                token=auth_res.session.access_token,
                user=UserProfile(
                    id=profile_id,
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

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [LOGIN ERROR]: {type(e).__name__} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication error: {str(e)}"
        )


@router.get("/verify-invite")
async def verify_invite(token: str, db: Session = Depends(get_db)):
    query = text("""
        SELECT name, email, account_status, token_expires_at 
        FROM company_employees 
        WHERE activation_token = :token
    """)
    employee = db.execute(query, {"token": token}).mappings().fetchone()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid activation token."
        )

    if employee["account_status"] == "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account has already been activated."
        )

    expires_at = employee["token_expires_at"]
    if expires_at:
        # Normalize datetime to UTC for accurate comparison
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Activation link has expired. Please contact your administrator."
            )

    return {
        "fullName": employee["name"],
        "email": employee["email"],
        "role": "employee"
    }


@router.post("/activate-account")
async def activate_account(payload: ActivateAccountSchema, db: Session = Depends(get_db)):
    # 1. Verify token existence
    query = text("""
        SELECT employee_id, name, email, account_status 
        FROM company_employees 
        WHERE activation_token = :token
    """)
    employee = db.execute(query, {"token": payload.token}).mappings().fetchone()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid activation token."
        )

    if employee["account_status"] == "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is already active."
        )

    # 2. Register user in Supabase Auth via Admin API
    try:
        user_attributes = {
            "email": employee["email"],
            "password": payload.password,
            "email_confirm": True,
            "user_metadata": {
                "full_name": employee["name"],
                "role": "employee"
            }
        }
        auth_res = supabase.auth.admin.create_user(user_attributes)
        supabase_uid = auth_res.user.id

    except Exception as err:
        err_str = str(err)
        if "already registered" in err_str.lower() or "already exists" in err_str.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This email address is already registered in the system."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Supabase user creation failed: {err_str}"
        )

    # 3. Mark record as ACTIVE and attach Supabase UID
    update_query = text("""
        UPDATE company_employees 
        SET account_status = 'ACTIVE',
            auth_user_id = :auth_id,
            activation_token = NULL,
            token_expires_at = NULL
        WHERE employee_id = :emp_id
    """)
    db.execute(update_query, {
        "auth_id": supabase_uid,
        "emp_id": employee["employee_id"]
    })
    db.commit()

    return {"message": "Account activated successfully. You may now log in."}