"""Pytest configuration and fixtures."""

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from packages.core.models import Base


@pytest.fixture
def api_docs_dir(monkeypatch):
    """Provide test api_docs directory."""
    test_api_docs_dir = Path(__file__).parent / "fixtures" / "api_docs"
    monkeypatch.setenv("API_DOCS_DIR", str(test_api_docs_dir))
    yield str(test_api_docs_dir)
    # Cleanup
    monkeypatch.delenv("API_DOCS_DIR", raising=False)


@pytest.fixture(scope="function")
def db_session():
    """Create a test database session."""
    # Use in-memory SQLite for tests
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine)
    session = session_local()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def test_client():
    """Create a test client."""
    from fastapi.testclient import TestClient

    from apps.api.main import app

    return TestClient(app)
