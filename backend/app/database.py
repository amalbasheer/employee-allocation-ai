import json
import os
from app.config import settings
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = getattr(settings, "DATABASE_URL", None) or os.getenv(
    "DATABASE_URL"
)

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is missing in environment variables.")

# Render is a persistent service, so standard connection pooling is optimal
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,             # Keep up to 10 active connections in memory
    max_overflow=20,          # Allow up to 20 additional temporary connections under load
    pool_timeout=30,          # Seconds to wait before throwing a timeout error
    pool_recycle=1800,        # Recycle connections every 30 minutes to prevent stale sockets
    pool_pre_ping=True,       # Automatically check connection health before executing queries
    json_serializer=lambda obj: json.dumps(obj, default=str),
    connect_args={
        "connect_timeout": 10,
        "options": "-c prepare_threshold=0",  # Prevents prepared statement errors with Supabase PgBouncer
    },
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db():
    """Call this manually or via a startup event / migration script."""
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