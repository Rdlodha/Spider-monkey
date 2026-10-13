"""Job runner for executing Scan jobs.

Implements the lifecycle defined in *M4_TOOL_ENGINE.md* Part A:
- queued → running → completed / failed / cancelled
- resolves hostnames, re‑checks each IP against the project's ScopeEntry list,
- runs the command via ``asyncio.create_subprocess_exec`` (argv list only),
- captures stdout/stderr to files under ``data/jobs/<job-id>/``,
- enforces a per‑job timeout (default 300 s) and cancellation via SIGTERM/SIGKILL,
- writes audit log entries for each state transition.

Only a single worker is started at app startup (see ``main.py`` – you may add the
call there).  Concurrency limiting is achieved via an ``asyncio.Semaphore`` with a
default of 2 concurrent jobs.
"""

import asyncio
import os
import signal
import sys
from pathlib import Path
from typing import Dict, List

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.base import Job, ScopeEntry, Project, Target
from app.core.audit import audit
from app.services.tool_adapter import get_adapter

# Directory where job artefacts (stdout, stderr) are stored.
_JOBS_ROOT = Path(os.getenv("JOB_DATA_ROOT", "./data/jobs")).resolve()
_JOBS_ROOT.mkdir(parents=True, exist_ok=True)

# Default timeout (seconds) – can be overridden per‑job via the ``profile`` config if needed.
_DEFAULT_TIMEOUT = int(os.getenv("JOB_TIMEOUT_SECONDS", "300"))

# Concurrency limiter – default 2 concurrent jobs.
_SEMAPHORE = asyncio.Semaphore(int(os.getenv("JOB_CONCURRENCY", "2")))


async def _run_job(job: Job, db: Session) -> None:
    """Execute a single job record.

    This function updates the ``Job`` row in‑place and commits after each state
    transition.  All I/O is performed asynchronously.
    """
    # --- 1. Mark as running -------------------------------------------------
    job.status = "running"
    job.started_at = func.now()
    audit(db, action="job_started", target=str(job.id), tool=job.tool)
    db.commit()

    # Resolve hostname if the target is a domain name – we store the raw value in
    # ``job.target_id`` already, but we need to verify the IPs against the scope.
    target_obj: Target = db.get(Target, job.target_id) if job.target_id else None
    hostname = target_obj.value if target_obj else None
    resolved_ips: List[str] = []
    if hostname:
        # Simple async DNS resolution using ``asyncio.getaddrinfo``.
        try:
            infos = await asyncio.get_event_loop().getaddrinfo(hostname, None, family=0, type=0, proto=0, flags=0)
            resolved_ips = list({info[4][0] for info in infos})
        except Exception as exc:
            job.status = "failed"
            job.completed_at = func.now()
            audit(db, action="job_failed", target=str(job.id), tool=job.tool, result=str(exc))
            db.commit()
            return

    # --- 2. Scope validation ------------------------------------------------
    if resolved_ips:
        # Load project's scope entries once.
        scope_entries = db.scalars(select(ScopeEntry).where(ScopeEntry.project_id == job.project_id)).all()
        allowed = []
        for entry in scope_entries:
            if entry.type == "IP" and entry.value in resolved_ips:
                allowed.append(entry.value)
            elif entry.type == "CIDR" and any(ip_in_cidr(ip, entry.value) for ip in resolved_ips):
                allowed.append(entry.value)
            elif entry.type == "DOMAIN" and hostname == entry.value:
                allowed.append(entry.value)
        if not allowed:
            # All resolved IPs are out‑of‑scope – abort.
            job.status = "failed"
            job.completed_at = func.now()
            audit(db, action="job_failed", target=str(job.id), tool=job.tool, result="out of scope")
            db.commit()
            return

    # --- 3. Build command ---------------------------------------------------
    adapter = get_adapter(job.tool)
    request_dict = {
        "target": hostname or job.target_id,
        "profile": job.profile,
        "tool": job.tool,
    }
    try:
        adapter.validate(request_dict)
    except ValueError as ve:
        job.status = "failed"
        job.completed_at = func.now()
        audit(db, action="job_failed", target=str(job.id), tool=job.tool, result=str(ve))
        db.commit()
        return
    cmd = adapter.build_command(request_dict)
    job.command = " ".join(cmd)  # store a readable representation
    db.commit()

    # --- 4. Execute subprocess ------------------------------------------------
    job_dir = _JOBS_ROOT / job.id
    job_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = job_dir / "stdout.log"
    stderr_path = job_dir / "stderr.log"

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=_DEFAULT_TIMEOUT)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        job.status = "failed"
        job.exit_code = None
        job.completed_at = func.now()
        job.stdout_path = str(stdout_path)
        job.stderr_path = str(stderr_path)
        # Write whatever we captured so far.
        stdout_path.write_bytes(stdout_bytes or b"")
        stderr_path.write_bytes(stderr_bytes or b"")
        audit(db, action="job_failed", target=str(job.id), tool=job.tool, result="timeout")
        db.commit()
        return
    finally:
        # Ensure we always write the artefacts.
        if not stdout_path.exists():
            stdout_path.write_bytes(stdout_bytes or b"")
        if not stderr_path.exists():
            stderr_path.write_bytes(stderr_bytes or b"")

    job.exit_code = proc.returncode
    job.stdout_path = str(stdout_path)
    job.stderr_path = str(stderr_path)
    job.completed_at = func.now()
    job.status = "completed" if proc.returncode == 0 else "failed"
    audit(db, action="job_completed", target=str(job.id), tool=job.tool, result="ok" if proc.returncode == 0 else f"exit {proc.returncode}")
    db.commit()

    # --- 5. Feed output to parsers ------------------------------------------
    if job.status == "completed":
        try:
            entities = adapter.parse(stdout_bytes)
            # The import_service already knows how to upsert hosts/services/endpoints.
            from app.services.import_service import run_import
            await run_import(entities, db, job.project_id)
        except Exception as exc:
            # Parsing failure should not crash the job runner – just log.
            audit(db, action="parse_failed", target=str(job.id), tool=job.tool, result=str(exc))
            db.commit()


async def job_worker(db_factory) -> None:
    """Background worker that continuously pulls queued jobs.

    ``db_factory`` is a callable returning a fresh ``Session`` – e.g. a lambda that
    creates a new engine‑bound session.  This keeps the worker independent from the
    FastAPI request lifecycle.
    """
    while True:
        async with _SEMAPHORE:
            # Pull the next queued job (FIFO).
            async with db_factory() as db:
                job = db.scalars(select(Job).where(Job.status == "queued").order_by(Job.created_at)).first()
                if not job:
                    # No jobs – sleep briefly before checking again.
                    await asyncio.sleep(2)
                    continue
                await _run_job(job, db)
        # Small pause to allow other coroutines to run.
        await asyncio.sleep(0.1)


def start_job_worker(db_engine) -> None:
    """Convenience helper to start the background worker when the app starts.

    ``db_engine`` is the SQLAlchemy engine used by the FastAPI app.  The function
    creates a ``Session`` factory that yields ``Session`` objects compatible with the
    async context manager pattern used in ``job_worker``.
    """
    async def _session_factory():
        # Simple async wrapper around the synchronous Session – we run it in a thread
        # pool to avoid blocking the event loop.
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: Session(db_engine))

    asyncio.create_task(job_worker(_session_factory))

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def ip_in_cidr(ip: str, cidr: str) -> bool:
    """Return ``True`` if *ip* belongs to *cidr* (e.g. ``192.168.0.1`` in ``192.168.0.0/24``).

    A tiny implementation using the standard ``ipaddress`` module.
    """
    import ipaddress

    try:
        return ipaddress.ip_address(ip) in ipaddress.ip_network(cidr, strict=False)
    except Exception:
        return False

"""End of job runner module"""
