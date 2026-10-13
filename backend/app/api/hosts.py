"""
Hosts API:
  GET    /api/hosts                           — list hosts (optional ?project_id filter, ?is_interesting)
  GET    /api/hosts/{id}                      — host detail with embedded services
  PATCH  /api/hosts/{id}/interesting          — toggle is_interesting on host
  PATCH  /api/hosts/services/{id}/interesting — toggle is_interesting on service
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.api.projects import get_db
from app.models.base import Host, Service
from app.schemas.scan import HostSummary, HostDetail, ServiceResponse

router = APIRouter()


@router.get("", response_model=list[HostSummary])
def list_hosts(
    project_id: str | None = None,
    is_interesting: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Host)
    if project_id:
        q = q.filter(Host.project_id == project_id)
    if is_interesting is not None:
        q = q.filter(Host.is_interesting == is_interesting)
    return q.order_by(Host.ip).all()


@router.get("/{host_id}", response_model=HostDetail)
def get_host(host_id: str, db: Session = Depends(get_db)):
    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    return host


@router.patch("/{host_id}/interesting", response_model=HostSummary)
def toggle_host_interesting(host_id: str, db: Session = Depends(get_db)):
    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    host.is_interesting = not host.is_interesting
    db.commit()
    db.refresh(host)
    return host


@router.patch("/services/{service_id}/interesting", response_model=ServiceResponse)
def toggle_service_interesting(service_id: str, db: Session = Depends(get_db)):
    svc = db.query(Service).filter(Service.id == service_id).first()
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")
    svc.is_interesting = not svc.is_interesting
    db.commit()
    db.refresh(svc)
    return svc
