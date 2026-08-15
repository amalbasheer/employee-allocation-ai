# backend/seed.py
import sys
import os

print(">>> [1/5] Starting seed.py script...", flush=True)

# 1. Verify working directory & .env file
if not os.path.exists(".env"):
    print("❌ ERROR: Could not find '.env' file in the current working directory!", flush=True)
    print(f"Current Directory: {os.getcwd()}", flush=True)
    sys.exit(1)

print(">>> [2/5] Loading environment configuration...", flush=True)

try:
    from app.config import settings
    print(f">>> Config Loaded. Connecting to: {settings.DATABASE_URL[:25]}...", flush=True)
except Exception as e:
    print(f"❌ ERROR loading configuration: {e}", flush=True)
    sys.exit(1)

# 2. Connect to DB and create tables
print(">>> [3/5] Connecting to Supabase and creating tables...", flush=True)

try:
    from app.database import init_db, SessionLocal
    from app.models.taxonomy import Skill, Designation

    init_db()
    print("✅ Database extensions and tables created successfully!", flush=True)
except Exception as e:
    print(f"❌ ERROR connecting/initializing database: {e}", flush=True)
    sys.exit(1)

# 3. Load the embedding generator (ai_engine)
print(">>> [4/5] Loading embedding model...", flush=True)

try:
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "ai_engine"))
    from embedding import generate_embeddings_batch
    print("✅ Embedding module loaded.", flush=True)
except Exception as e:
    print(f"❌ ERROR loading embedding module: {e}", flush=True)
    sys.exit(1)

# 4. Seed initial data — WITH embeddings this time
print(">>> [5/5] Seeding master taxonomy data...", flush=True)

db = SessionLocal()
try:
    if not db.query(Skill).first():
        print("Generating embeddings for master skills...", flush=True)
        skill_data = [
            ("Python", "tech_stack"),
            ("FastAPI", "tech_stack"),
            ("React.js", "tech_stack"),
            ("PostgreSQL", "tech_stack"),
            ("Machine Learning", "domain"),
            ("Computer Vision", "domain"),
        ]
        names = [name for name, _ in skill_data]
        vectors = generate_embeddings_batch(names)

        print("Inserting master skills (with embeddings)...", flush=True)
        skills = [
            Skill(name=name, category=category, skill_embedding=vector)
            for (name, category), vector in zip(skill_data, vectors)
        ]
        db.add_all(skills)
        db.commit()
        print("✅ Skills inserted.", flush=True)
    else:
        print("ℹ️ Skills already seeded, skipping.", flush=True)

    if not db.query(Designation).first():
        print("Inserting master designations...", flush=True)
        designations = [
            Designation(title="Senior AI Engineer", department="AI/ML"),
            Designation(title="Fullstack Developer", department="Web Dev"),
        ]
        db.add_all(designations)
        db.commit()
        print("✅ Designations inserted.", flush=True)
    else:
        print("ℹ️ Designations already seeded, skipping.", flush=True)

    print("🎉 SUCCESS: Seeding complete!", flush=True)

except Exception as e:
    db.rollback()
    print(f"❌ ERROR during seeding: {e}", flush=True)
finally:
    db.close()