import pytest
import os
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Setup test environment variables BEFORE importing app
TEST_TOKEN = "test_token"
TEST_TOKEN_FILE = Path(__file__).parent / ".test_token"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["LOCAL_TOKEN_PATH"] = str(TEST_TOKEN_FILE)

from app.core.config import settings
settings.local_token_path = str(TEST_TOKEN_FILE)

from app.main import app
from app.models.base import Base, Project, Target, AuditLog, Scan, Host, Service, Endpoint
from app.api.projects import get_db

# Create SQLite in-memory tables
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
)
Base.metadata.create_all(bind=engine)


@pytest.fixture(autouse=True)
def setup_token():
    """Ensure the test token file always exists with the known test token."""
    TEST_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TEST_TOKEN_FILE.write_text(TEST_TOKEN, encoding="utf-8")
    yield
    try:
        if TEST_TOKEN_FILE.exists():
            TEST_TOKEN_FILE.unlink()
    except Exception:
        pass


@pytest.fixture
def db_session():
    """Isolated session per test: all database changes are rolled back."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    """TestClient configured with dependency overrides for the isolated test DB session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)
