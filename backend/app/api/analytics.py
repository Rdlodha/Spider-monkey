"""Correlation API and Dashboard stats."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.projects import get_db
from app.models.base import Host, Service, Endpoint, Finding, ChecklistProgress
from app.schemas.findings import CorrelationResult, DashboardStats
from app.services.correlation import run_correlation

router = APIRouter()


@router.get("/correlate/{project_id}", response_model=CorrelationResult)
def correlate(project_id: str, db: Session = Depends(get_db)):
    suggestions = run_correlation(db, project_id)
    return CorrelationResult(project_id=project_id, suggestions=suggestions)


@router.get("/dashboard/{project_id}", response_model=DashboardStats)
def dashboard(project_id: str, db: Session = Depends(get_db)):
    host_count = db.query(Host).filter(Host.project_id == project_id).count()

    open_port_count = (
        db.query(Service)
        .join(Host, Host.id == Service.host_id)
        .filter(Host.project_id == project_id, Service.state == "open")
        .count()
    )

    endpoint_count = db.query(Endpoint).filter(Endpoint.project_id == project_id).count()

    findings_q = db.query(Finding).filter(Finding.project_id == project_id)
    finding_count = findings_q.count()
    critical_finding_count = findings_q.filter(Finding.severity == "CRITICAL").count()
    high_finding_count = (
        db.query(Finding)
        .filter(Finding.project_id == project_id, Finding.severity == "HIGH")
        .count()
    )

    # Checklist progress across all targets in this project
    from app.models.base import Target
    target_ids = [t.id for t in db.query(Target).filter(Target.project_id == project_id).all()]
    checklist_total = 0
    checklist_completed = 0
    if target_ids:
        checklist_total = (
            db.query(ChecklistProgress)
            .filter(ChecklistProgress.target_id.in_(target_ids))
            .count()
        )
        checklist_completed = (
            db.query(ChecklistProgress)
            .filter(
                ChecklistProgress.target_id.in_(target_ids),
                ChecklistProgress.state == "COMPLETED",
            )
            .count()
        )

    return DashboardStats(
        project_id=project_id,
        host_count=host_count,
        open_port_count=open_port_count,
        endpoint_count=endpoint_count,
        finding_count=finding_count,
        critical_finding_count=critical_finding_count,
        high_finding_count=high_finding_count,
        checklist_completed=checklist_completed,
        checklist_total=checklist_total,
    )
