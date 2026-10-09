from fastapi import APIRouter, Depends, HTTPException
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
