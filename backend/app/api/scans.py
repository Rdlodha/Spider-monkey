"""
Scans API:
  POST   /api/scans/import   — multipart upload: project_id, target_id, tool, file
  GET    /api/scans           — list all scans (optional ?project_id filter)
  GET    /api/scans/{id}      — scan detail with embedded hosts + endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.api.projects import get_db
from app.models.base import Scan
from app.schemas.scan import ScanSummary, ScanDetail
from app.services.import_service import run_import, MAX_UPLOAD_BYTES
from app.core.audit import audit

router = APIRouter()


@router.post("/import", response_model=ScanSummary)
async def import_scan(
    project_id: str = Form(...),
    tool: str = Form(...),
    target_id: str | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Import a tool output file.
    Supported tools: nmap, feroxbuster, gobuster.
    File size limit: 50 MB.
    """
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit",
        )

    try:
        scan = run_import(
            db=db,
            project_id=project_id,
            target_id=target_id or None,
            tool=tool.lower().strip(),
            raw_content=content,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    audit(db, action="import_scan", target=scan.id, tool=tool, result=scan.status)
    return scan


@router.get("", response_model=list[ScanSummary])
def list_scans(project_id: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Scan)
    if project_id:
        q = q.filter(Scan.project_id == project_id)
    return q.order_by(Scan.created_at.desc()).all()


@router.get("/{scan_id}", response_model=ScanDetail)
def get_scan(scan_id: str, db: Session = Depends(get_db)):
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan
