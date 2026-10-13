"""API endpoints for the Tool Engine (Part A & B integration).

- ``POST /api/engine/scans/request`` creates a ``Job`` after validating that the target is in-scope.
- ``GET  /api/engine/jobs``           list all jobs (optional ?project_id filter).
- ``GET  /api/engine/jobs/{job_id}``  returns status and artefact URLs.
- ``GET  /api/engine/jobs/{job_id}/stdout`` download raw stdout log.
- ``GET  /api/engine/jobs/{job_id}/stderr`` download raw stderr log.
- ``POST /api/engine/jobs/{job_id}/cancel`` cancels a running job.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from typing import Optional

from app.api.projects import get_db
from app.core.audit import audit
from app.models.base import Job, ScopeEntry, Target, Project

router = APIRouter()


# ── helpers ──────────────────────────────────────────────────────────────────

def _resolve_target(db: Session, target_value: str, project_id: str) -> Target:
    """Return existing Target or create a new one."""
    target = db.scalars(
        select(Target).where(Target.project_id == project_id, Target.value == target_value)
    ).first()
    if not target:
        target = Target(project_id=project_id, value=target_value)
        db.add(target)
        db.commit()
        db.refresh(target)
    return target


def _job_to_dict(job: Job) -> dict:
    return {
        "id": job.id,
        "project_id": job.project_id,
        "target_id": job.target_id,
        "tool": job.tool,
        "profile": job.profile,
        "status": job.status,
        "exit_code": job.exit_code,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "created_at": job.created_at,
        "proxy_profile_id": job.proxy_profile_id,
        "stdout_url": f"/api/engine/jobs/{job.id}/stdout" if job.stdout_path else None,
        "stderr_url": f"/api/engine/jobs/{job.id}/stderr" if job.stderr_path else None,
    }


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.post("/scans/request", status_code=status.HTTP_202_ACCEPTED)
def request_scan(
    *,
    db: Session = Depends(get_db),
    project_id: str,
    target: str,
    tool: str,
    profile: str,
    proxy_profile_id: Optional[str] = None,
) -> dict:
    """Validate scope, create a Job and queue it."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    target_obj = _resolve_target(db, target, project_id)

    # API-level scope check (execution-time DNS rebinding check is in the job runner).
    allowed = db.scalars(select(ScopeEntry).where(ScopeEntry.project_id == project_id)).all()
    if not any(
        (se.type == "IP" and se.value == target) or (se.type == "DOMAIN" and se.value == target)
        for se in allowed
    ):
        raise HTTPException(status_code=400, detail="Target is out of scope")

    job = Job(
        project_id=project_id,
        target_id=target_obj.id,
        tool=tool,
        profile=profile,
        status="queued",
        proxy_profile_id=proxy_profile_id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    audit(db, action="job_queued", target=str(job.id), tool=tool, result="queued")
    return _job_to_dict(job)


@router.get("/jobs")
def list_jobs(
    project_id: Optional[str] = None,
    db: Session = Depends(get_db),
) -> list:
    """List all jobs, optionally filtered by project."""
    q = select(Job).order_by(Job.created_at.desc())
    if project_id:
        q = q.where(Job.project_id == project_id)
    jobs = db.scalars(q).all()
    return [_job_to_dict(j) for j in jobs]


@router.get("/jobs/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)) -> dict:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_dict(job)


@router.get("/jobs/{job_id}/stdout")
def download_stdout(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job or not job.stdout_path:
        raise HTTPException(status_code=404, detail="Stdout not available")
    return FileResponse(job.stdout_path, media_type="text/plain", filename="stdout.log")


@router.get("/jobs/{job_id}/stderr")
def download_stderr(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job or not job.stderr_path:
        raise HTTPException(status_code=404, detail="Stderr not available")
    return FileResponse(job.stderr_path, media_type="text/plain", filename="stderr.log")


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in {"queued", "running"}:
        raise HTTPException(status_code=400, detail="Job cannot be cancelled in its current state")
    job.status = "cancelled"
    job.completed_at = func.now()
    db.commit()
    audit(db, action="job_cancelled", target=str(job.id), tool=job.tool)
    return _job_to_dict(job)
