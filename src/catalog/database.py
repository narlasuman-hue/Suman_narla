"""Database connection and session management."""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from typing import Generator

from src.config import settings
from src.catalog.models import Base

# Create engine with connection pooling
engine = create_engine(
    settings.get_database_url(),
    echo=settings.debug,
    poolclass=NullPool if settings.debug else None,
    pool_pre_ping=True,  # Verify connections before using
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Get database session as dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database schema."""
    Base.metadata.create_all(bind=engine)


def drop_db() -> None:
    """Drop all tables (for testing/cleanup)."""
    Base.metadata.drop_all(bind=engine)


def get_session() -> Session:
    """Get a single database session."""
    return SessionLocal()
