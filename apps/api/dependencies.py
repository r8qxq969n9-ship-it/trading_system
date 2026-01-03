"""FastAPI dependencies."""

from sqlalchemy.orm import Session

from packages.core.database import get_session_factory

SessionLocal = get_session_factory()


def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
