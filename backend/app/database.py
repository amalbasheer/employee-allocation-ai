# backend/app/database.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.config import settings
import json

if not settings.DATABASE_URL:
    raise ValueError("DATABASE_URL is missing in .env file.")

# Added connect_args timeout so it never hangs silently
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
    json_serializer=lambda obj: json.dumps(obj, default=str),
    connect_args={"connect_timeout": 10}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def init_db():
    """Initializes PostgreSQL extensions and creates tables."""
    with engine.begin() as conn:
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS vector;'))
    
    import app.models  # Register ORM models
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()