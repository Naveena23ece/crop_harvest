"""
Database configuration and session management for GrainGuard AI.
Uses SQLite for zero-configuration, robust local persistence.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(DATA_DIR, "grainguard.db"))
DATABASE_URL = f"sqlite:///{DB_PATH}"

# connect_args={"check_same_thread": False} is required for SQLite with FastAPI
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency yielding a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
