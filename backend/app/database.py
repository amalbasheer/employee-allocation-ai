import json
import os
from app.config import settings
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool  # Required for AWS Lambda + Supabase

DATABASE_URL = getattr(settings, "DATABASE_URL", None) or os.getenv(
    "DATABASE_URL"
)

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is missing in environment variables.")

# NullPool prevents connection leaks on serverless invocations
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    echo=False,
    json_serializer=lambda obj: json.dumps(obj, default=str),
    connect_args={"connect_timeout": 10},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db():
    """Call this manually or via a migration script, NOT on Lambda startup."""
    with engine.begin() as conn:
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

    import app.models

    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()