"""Findings API: CRUD + link management + evidence upload/text paste."""
import io
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path

from app.api.projects import get_db
from app.models.base import Finding, FindingLink, Evidence
from app.schemas.findings import (
    FindingCreate, FindingUpdate,
    FindingDetail, FindingSummary,
    FindingLinkSchema, FindingLinkResponse,
    EvidenceResponse,
)
from app.services import findings_service

router = APIRouter()


def _get_finding_or_404(finding_id: str, db: Session) -> Finding:
    f = db.query(Finding).filter_by(id=finding_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Finding not found")
    return f


# ── CRUD ───────────────────────────────────────────────────────────────────────

@router.post("", response_model=FindingDetail)
def create_finding(data: FindingCreate, db: Session = Depends(get_db)):
    return findings_service.create_finding(db, data)


@router.get("", response_model=list[FindingSummary])
def list_findings(
    project_id: str,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    tag: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Finding).filter(Finding.project_id == project_id)
    if severity:
        q = q.filter(Finding.severity == severity.upper())
    if status:
        q = q.filter(Finding.status == status.upper())
    if tag:
        q = q.filter(Finding.tags.contains(tag))
    return q.order_by(Finding.created_at.desc()).all()


@router.get("/{finding_id}", response_model=FindingDetail)
def get_finding(finding_id: str, db: Session = Depends(get_db)):
    return _get_finding_or_404(finding_id, db)


@router.patch("/{finding_id}", response_model=FindingDetail)
def update_finding(finding_id: str, data: FindingUpdate, db: Session = Depends(get_db)):
    f = _get_finding_or_404(finding_id, db)
    return findings_service.update_finding(db, f, data)


@router.delete("/{finding_id}", status_code=204)
def delete_finding(finding_id: str, db: Session = Depends(get_db)):
    f = _get_finding_or_404(finding_id, db)
    findings_service.delete_finding(db, f)


# ── Links ──────────────────────────────────────────────────────────────────────

@router.post("/{finding_id}/links", response_model=FindingLinkResponse)
def add_link(finding_id: str, link: FindingLinkSchema, db: Session = Depends(get_db)):
    _get_finding_or_404(finding_id, db)
    return findings_service.add_link(db, finding_id, link.entity_type, link.entity_id)


@router.delete("/{finding_id}/links/{link_id}", status_code=204)
def remove_link(finding_id: str, link_id: str, db: Session = Depends(get_db)):
    link = db.query(FindingLink).filter_by(id=link_id, finding_id=finding_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    findings_service.remove_link(db, link)


# ── Evidence ──────────────────────────────────────────────────────────────────

@router.post("/{finding_id}/evidence/file", response_model=EvidenceResponse)
async def upload_evidence(
    finding_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    _get_finding_or_404(finding_id, db)
    file_bytes = await file.read()
    try:
        ev = findings_service.save_evidence_file(
            db, finding_id, file.filename or "upload", file_bytes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ev


@router.post("/{finding_id}/evidence/text", response_model=EvidenceResponse)
def paste_evidence(
    finding_id: str,
    text: str = Form(...),
    db: Session = Depends(get_db),
):
    _get_finding_or_404(finding_id, db)
    return findings_service.save_evidence_text(db, finding_id, text)


@router.get("/{finding_id}/evidence/{evidence_id}/download")
def download_evidence(finding_id: str, evidence_id: str, db: Session = Depends(get_db)):
    ev = db.query(Evidence).filter_by(id=evidence_id, finding_id=finding_id).first()
    if not ev or not ev.path:
        raise HTTPException(status_code=404, detail="Evidence file not found")
    p = Path(ev.path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Evidence file missing from disk")
    return FileResponse(
        path=str(p),
        media_type=ev.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{ev.original_filename or p.name}"'},
    )


@router.delete("/{finding_id}/evidence/{evidence_id}", status_code=204)
def delete_evidence(finding_id: str, evidence_id: str, db: Session = Depends(get_db)):
    ev = db.query(Evidence).filter_by(id=evidence_id, finding_id=finding_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")
    findings_service.delete_evidence(db, ev)
