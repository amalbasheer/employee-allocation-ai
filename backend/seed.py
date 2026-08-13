# backend/seed.py
import sys
import os

print(">>> [1/4] Starting seed.py script...", flush=True)

# 1. Verify working directory & .env file
if not os.path.exists(".env"):
    print("❌ ERROR: Could not find '.env' file in the current working directory!", flush=True)
    print(f"Current Directory: {os.getcwd()}", flush=True)
    sys.exit(1)

print(">>> [2/4] Loading environment configuration...", flush=True)

try:
    from app.config import settings
    print(f">>> Config Loaded. Connecting to: {settings.DATABASE_URL[:25]}...", flush=True)
except Exception as e:
    print(f"❌ ERROR loading configuration: {e}", flush=True)
    sys.exit(1)

# 2. Test database connection with timeout
print(">>> [3/4] Connecting to Supabase and creating tables...", flush=True)

try:
    from app.database import init_db, SessionLocal
    from app.models.taxonomy import Skill, Designation
    
    init_db()
    print("✅ Database extensions and tables created successfully!", flush=True)
except Exception as e:
    print(f"❌ ERROR connecting/initializing database: {e}", flush=True)
    sys.exit(1)

# 3. Seed initial data
print(">>> [4/4] Seeding master taxonomy data...", flush=True)

db = SessionLocal()
try:
    existing_skills = db.query(Skill).first()
    if existing_skills:
        print("ℹ️ Database is already seeded. Skipping insert.", flush=True)
    else:
        print("Inserting master skills...", flush=True)
        skills = [
            Skill(skill_name="Python", category="tech_stack"),
            Skill(skill_name="FastAPI", category="tech_stack"),
            Skill(skill_name="React.js", category="tech_stack"),
            Skill(skill_name="PostgreSQL", category="tech_stack"),
            Skill(skill_name="Machine Learning", category="domain"),
            Skill(skill_name="Computer Vision", category="domain")
        ]
        db.add_all(skills)

        print("Inserting master designations...", flush=True)
        designations = [
            Designation(title="Senior AI Engineer", department="AI/ML"),
            Designation(title="Fullstack Developer", department="Web Dev")
        ]
        db.add_all(designations)
        
        db.commit()
        print("🎉 SUCCESS: Master data inserted into Supabase!", flush=True)

except Exception as e:
    db.rollback()
    print(f"❌ ERROR during seeding: {e}", flush=True)
finally:
    db.close()