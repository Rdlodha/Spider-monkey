import os

def create_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

FILES = {
    "backend/app/__init__.py": "",
    "backend/app/core/__init__.py": "",
    "backend/app/api/__init__.py": "",
    "backend/app/models/__init__.py": "",
    "backend/app/schemas/__init__.py": "",
    "backend/app/services/__init__.py": "",
    "backend/tests/__init__.py": "",
    
    "backend/app/core/config.py": """from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://reconforge:reconforge@localhost:5432/reconforge"
    frontend_origin: str = "http://localhost:5173"
    local_token_path: str = "backend/.local/token"
    host: str = "127.0.0.1"
    port: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
""",
    "backend/app/core/security.py": """import os
import secrets
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from fastapi import Request
from .config import settings

def ensure_token_exists():
    path = settings.local_token_path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        token = secrets.token_hex(32)
        with open(path, "w", encoding="utf-8") as f:
            f.write(token)
        try:
            os.chmod(path, 0o600)
        except Exception:
            pass # Windows or other OS might not support 0o600

class BearerTokenMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api/health"):
            return await call_next(request)
        if request.url.path.startswith("/api"):
            auth_header = request.headers.get("Authorization")
            
            with open(settings.local_token_path, "r", encoding="utf-8") as f:
                expected_token = f.read().strip()
                
            if not auth_header or not auth_header.startswith("Bearer "):
                return JSONResponse({"detail": "Unauthorized"}, status_code=401)
                
            token = auth_header.split(" ")[1]
            if token != expected_token:
                return JSONResponse({"detail": "Unauthorized"}, status_code=401)
                
        return await call_next(request)
""",
    "backend/app/models/base.py": """import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Project(Base):
    __tablename__ = "project"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    authorized_ack_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    
    targets: Mapped[list["Target"]] = relationship("Target", back_populates="project", cascade="all, delete-orphan")

class Target(Base):
    __tablename__ = "target"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    value: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    
    project: Mapped["Project"] = relationship("Project", back_populates="targets")

class AuditLog(Base):
    __tablename__ = "audit_log"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ts: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    actor: Mapped[str] = mapped_column(String(50), default="local", server_default="local", nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target: Mapped[str] = mapped_column(String(500), nullable=True)
    tool: Mapped[str] = mapped_column(String(100), nullable=True)
    result: Mapped[str] = mapped_column(String(100), nullable=True)
""",
    "backend/app/core/audit.py": """from sqlalchemy.orm import Session
from app.models.base import AuditLog

def audit(db: Session, action: str, target: str = None, tool: str = None, result: str = None):
    log = AuditLog(action=action, target=target, tool=tool, result=result)
    db.add(log)
    db.commit()
""",
    "backend/app/api/health.py": """from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health_check():
    return {"status": "ok", "application": "ReconForge"}
""",
    "backend/app/schemas/project.py": """from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class TargetBase(BaseModel):
    value: str

class TargetCreate(TargetBase):
    pass

class TargetResponse(TargetBase):
    id: str
    project_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ProjectBase(BaseModel):
    name: str

class ProjectCreate(ProjectBase):
    authorized_ack: bool = Field(..., description="Must be true to authorize testing targets")

class ProjectResponse(ProjectBase):
    id: str
    authorized_ack_at: Optional[datetime]
    created_at: datetime
    targets: List[TargetResponse] = []
    
    class Config:
        from_attributes = True
""",
    "backend/app/api/projects.py": """from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from app.models.base import Project, Target
from app.schemas.project import ProjectCreate, ProjectResponse, TargetCreate, TargetResponse
from app.core.audit import audit
from app.core.config import settings
from datetime import datetime

router = APIRouter()

# DB dependency
engine = create_engine(settings.database_url)
def get_db():
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()

@router.post("", response_model=ProjectResponse)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    if not project.authorized_ack:
        raise HTTPException(status_code=400, detail="Must acknowledge authorization")
        
    db_project = Project(
        name=project.name,
        authorized_ack_at=datetime.utcnow()
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    
    audit(db, action="create_project", target=db_project.id)
    return db_project

@router.get("", response_model=list[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).all()

@router.post("/{project_id}/targets", response_model=TargetResponse)
def add_target(project_id: str, target: TargetCreate, db: Session = Depends(get_db)):
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    db_target = Target(project_id=project_id, value=target.value)
    db.add(db_target)
    db.commit()
    db.refresh(db_target)
    
    audit(db, action="add_target", target=db_target.id)
    return db_target

@router.get("/{project_id}/targets", response_model=list[TargetResponse])
def list_targets(project_id: str, db: Session = Depends(get_db)):
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    return db.query(Target).filter(Target.project_id == project_id).all()
""",
    "backend/app/api/targets.py": """from fastapi import APIRouter
router = APIRouter()
""",
    "backend/app/api/router.py": """from fastapi import APIRouter
from .health import router as health_router
from .projects import router as projects_router
from .targets import router as targets_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(projects_router, prefix="/projects", tags=["projects"])
api_router.include_router(targets_router, prefix="/targets", tags=["targets"])
""",
    "backend/app/main.py": """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.security import BearerTokenMiddleware, ensure_token_exists
from app.api.router import api_router

def create_app():
    ensure_token_exists()
    
    app = FastAPI(title="ReconForge")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(BearerTokenMiddleware)
    
    app.include_router(api_router, prefix="/api")
    
    return app

app = create_app()
""",
    "backend/alembic/env.py": """from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from app.core.config import settings
from app.models.base import Base

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
""",
    "backend/alembic/script.py.mako": '"""${message}\n\nRevision ID: ${up_revision}\nRevises: ${down_revision | comma,n}\nCreate Date: ${create_date}\n\n"""\nfrom typing import Sequence, Union\n\nfrom alembic import op\nimport sqlalchemy as sa\n${imports if imports else ""}\n\n# revision identifiers, used by Alembic.\nrevision: str = ${repr(up_revision)}\ndown_revision: Union[str, None] = ${repr(down_revision)}\nbranch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}\ndepends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}\n\n\ndef upgrade() -> None:\n    ${upgrades if upgrades else "pass"}\n\n\ndef downgrade() -> None:\n    ${downgrades if downgrades else "pass"}\n',
    "backend/alembic/versions/0001_initial.py": """\"\"\"initial

Revision ID: 0001
Revises: 
Create Date: 2026-10-07
\"\"\"
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table('project',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('authorized_ack_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_table('target',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('project.id', ondelete='CASCADE'), nullable=False),
        sa.Column('value', sa.String(500), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_table('audit_log',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('ts', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('actor', sa.String(50), nullable=False, server_default='local'),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('target', sa.String(500), nullable=True),
        sa.Column('tool', sa.String(100), nullable=True),
        sa.Column('result', sa.String(100), nullable=True),
    )

def downgrade() -> None:
    op.drop_table('audit_log')
    op.drop_table('target')
    op.drop_table('project')
""",
    "backend/tests/conftest.py": """import pytest
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
""",
    "backend/tests/test_health.py": """def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "application": "ReconForge"}

def test_unauthorized(client):
    response = client.get("/api/projects")
    assert response.status_code == 401
    
def test_project_create_list(client):
    headers = {"Authorization": "Bearer test_token"}
    response = client.post("/api/projects", json={"name": "Test Proj", "authorized_ack": True}, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Proj"
    
    response2 = client.get("/api/projects", headers=headers)
    assert response2.status_code == 200
    assert len(response2.json()) == 1
    assert response2.json()[0]["name"] == "Test Proj"
"""
}

for path, content in FILES.items():
    create_file(path, content)
print("Backend setup complete.")
