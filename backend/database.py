"""
CAYE v3.0 — Database Connection & Session Management
PostgreSQL + SQLAlchemy + Connection Pooling
"""

import os
from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from loguru import logger

from backend.config import get_settings

settings = get_settings()

# ─────────────────────────────────────────
# CREATE ENGINE
# ─────────────────────────────────────────
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.app_debug,
)

# ─────────────────────────────────────────
# SESSION FACTORY
# ─────────────────────────────────────────
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ─────────────────────────────────────────
# BASE CLASS FOR ALL MODELS
# ─────────────────────────────────────────
Base = declarative_base()


# ─────────────────────────────────────────
# DATABASE SESSION DEPENDENCY
# Used by FastAPI route handlers
# ─────────────────────────────────────────
def get_db():
    """
    Yields a database session and ensures it
    is closed after the request completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─────────────────────────────────────────
# CONNECTION HEALTH CHECK
# ─────────────────────────────────────────
def check_database_connection() -> bool:
    """
    Tests database connectivity.
    Returns True if connection successful.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection: OK")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


# ─────────────────────────────────────────
# INITIALIZE DATABASE
# Creates all tables if they don't exist
# ─────────────────────────────────────────
def init_db():
    """
    Imports all models and creates all tables.
    Called on application startup.
    """
    try:
        from backend import models  # noqa: F401
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise