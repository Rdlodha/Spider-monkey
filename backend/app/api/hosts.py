"""
Hosts API:
  GET  /api/hosts          — list hosts (optional ?project_id filter)
  GET  /api/hosts/{id}     — host detail with embedded services
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.projects import get_db
from app.models.base import Host
from app.schemas.scan import HostSummary, HostDetail

router = APIRouter()


@router.get("", response_model=list[HostSummary])
def list_hosts(project_id: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Host)
    if project_id:
        q = q.filter(Host.project_id == project_id)
    return q.order_by(Host.ip).all()


@router.get("/{host_id}", response_model=HostDetail)
def get_host(host_id: str, db: Session = Depends(get_db)):
    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    return host
