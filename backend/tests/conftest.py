import pytest
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["LOCAL_TOKEN_PATH"] = "backend/.local/test_token"

from app.main import app
from app.models.base import Base
from app.api.projects import get_db

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = Session(engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        yield TestingSessionLocal
    finally:
        pass

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_token():
    os.makedirs("backend/.local", exist_ok=True)
    with open("backend/.local/token", "w") as f:
        f.write("test_token")
    yield
    try:
        os.remove("backend/.local/token")
    except:
        pass

@pytest.fixture
def client():
    return TestClient(app)
