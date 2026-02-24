"""
Shared pytest fixtures.

Uses a real PostgreSQL database for tests (banking_test on port 5433).
Override TEST_DATABASE_URL env var to point at a different instance.

To spin up the test DB locally:
    docker compose up db_test -d
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.main import app
from app.database import Base, get_db

engine = create_engine(settings.test_database_url)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    """Create all tables before each test, drop them after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)
