# check_skills.py
from sqlalchemy import inspect
from app.database import engine

inspector = inspect(engine)

if "skills" in inspector.get_table_names():
    print("\n✅ 'skills' table found. Columns in database:")
    for col in inspector.get_columns("skills"):
        print(f"  - Name: '{col['name']}' | Type: {col['type']}")
else:
    print("\n❌ 'skills' table DOES NOT exist in database!")