# app/api/deps.py
from typing import Generator
from app.database import SessionLocal

def get_db() -> Generator:
    """Yields a database session per request and closes it automatically."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()