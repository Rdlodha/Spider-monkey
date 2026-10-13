"""
Endpoints API:
  GET   /api/endpoints                — list endpoints (optional ?project_id filter, ?is_interesting)
  PATCH /api/endpoints/{id}/interesting — toggle is_interesting flag
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.api.projects import get_db
from app.models.base import Endpoint
from app.schemas.scan import EndpointResponse

router = APIRouter()


@router.get("", response_model=list[EndpointResponse])
def list_endpoints(
    project_id: Optional[str] = None,
    is_interesting: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Endpoint)
    if project_id:
        q = q.filter(Endpoint.project_id == project_id)
    if is_interesting is not None:
        q = q.filter(Endpoint.is_interesting == is_interesting)
    return q.order_by(Endpoint.url).all()


@router.patch("/{endpoint_id}/interesting", response_model=EndpointResponse)
def toggle_interesting(endpoint_id: str, db: Session = Depends(get_db)):
    ep = db.query(Endpoint).filter_by(id=endpoint_id).first()
    if not ep:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    ep.is_interesting = not ep.is_interesting
    db.commit()
    db.refresh(ep)
    return ep
