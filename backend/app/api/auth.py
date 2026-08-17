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
def login(credentials: LoginRequest):
    print(f"\n--- [LOGIN ATTEMPT] Email: {credentials.email} ---")
    
    try:
        # 1. Authenticate credentials via Supabase Auth
        print("--> Step 1: Calling supabase.auth.sign_in_with_password...")
        auth_res = supabase.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password
        })
        print("--> Step 1 COMPLETE: Auth successful.")

        if not auth_res.user or not auth_res.session:
            print("--> Step 1 FAILED: Missing user or session.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid email or password"
            )

        email = auth_res.user.email
        user_id = auth_res.user.id

        # 2. Check 'company_employees' table first
        print(f"--> Step 2: Querying company_employees table for {email}...")
        emp_query = supabase.table("company_employees").select("*").eq("email", email).execute()
        print(f"--> Step 2 COMPLETE: Found {len(emp_query.data if emp_query.data else [])} record(s).")
        
        if emp_query.data and len(emp_query.data) > 0:
            emp_data = emp_query.data[0]
            role = emp_data.get("role") or auth_res.user.user_metadata.get("role") or "employee"
            name = emp_data.get("name") or emp_data.get("full_name") or email.split("@")[0]
            # Use custom patterned employee_id if present, else fallback to auth user_id
            profile_id = emp_data.get("employee_id") or user_id

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
        print(f"--> Step 3 COMPLETE: Found {len(intern_query.data if intern_query.data else [])} record(s).")

        if intern_query.data and len(intern_query.data) > 0:
            intern_data = intern_query.data[0]
            role = "student"
            name = intern_data.get("name") or intern_data.get("full_name") or email.split("@")[0]
            profile_id = intern_data.get("intern_id") or user_id

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
        print("--> Step 4: User not found in profile tables, using fallback metadata.")
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
        # Preserve explicitly raised HTTP exceptions (e.g. 401)
        raise
    except Exception as e:
        print(f"❌ [LOGIN ERROR]: {type(e).__name__} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication error: {str(e)}"
        )