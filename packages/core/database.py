"""Database configuration and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from packages.core.models import Base


def get_database_url() -> str:
    """Get database URL from environment."""
    import os
    from urllib.parse import quote_plus

    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "postgres")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "trading_system")

    password_encoded = quote_plus(db_password)
    return f"postgresql://{db_user}:{password_encoded}@{db_host}:{db_port}/{db_name}"


def create_engine_from_env():
    """Create SQLAlchemy engine from environment."""
    database_url = get_database_url()
    return create_engine(database_url, echo=False)


def get_session_factory(engine=None):
    """Get session factory."""
    if engine is None:
        engine = create_engine_from_env()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(engine=None):
    """Initialize database (create tables)."""
    if engine is None:
        engine = create_engine_from_env()
    Base.metadata.create_all(bind=engine)
