"""FastAPI dependencies."""

from typing import Generator

from sqlalchemy.orm import Session

from packages.core.database import get_session_factory

SessionLocal = get_session_factory()


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
