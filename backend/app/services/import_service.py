"""
Import service: handles saving raw tool output, running the parser,
and upserting results into the database.

Rules:
- Raw file is saved to data/raw/<sha256> (never stored in a DB text column).
- Scan is created with status=running, then updated to completed or failed.
- All inserts are upserts: first_seen is set once; last_seen is always updated.
- Every derived record stores the scan_id it came from.
"""
import hashlib
import os
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session

from app.models.base import Scan, Host, Service, Endpoint
from app.parsers import ParseResult, ParsedHost, ParsedService, ParsedEndpoint
from app.parsers.registry import get_parser

# Maximum upload size: 50 MB
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
RAW_DIR = Path("data/raw")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _save_raw(data: bytes) -> tuple[str, str]:
    """Save raw bytes to data/raw/<sha256>. Returns (path, sha256)."""
    digest = _sha256(data)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    dest = RAW_DIR / digest
    if not dest.exists():
        dest.write_bytes(data)
    return str(dest), digest


def _upsert_host(db: Session, project_id: str, scan_id: str, h: ParsedHost, now: datetime) -> Host:
    existing = db.query(Host).filter_by(project_id=project_id, ip=h.ip).first()
    if existing:
        existing.last_seen = now
        existing.scan_id = scan_id
        if h.hostname:
            existing.hostname = h.hostname
        return existing
    host = Host(
        project_id=project_id,
        ip=h.ip,
        hostname=h.hostname,
        first_seen=now,
        last_seen=now,
        scan_id=scan_id,
    )
    db.add(host)
    db.flush()  # get .id
    return host


def _upsert_service(db: Session, host: Host, scan_id: str, s: ParsedService, now: datetime) -> Service:
    existing = db.query(Service).filter_by(
        host_id=host.id, protocol=s.protocol, port=s.port
    ).first()
    if existing:
        existing.last_seen = now
        existing.scan_id = scan_id
        existing.state = s.state
        if s.name:
            existing.name = s.name
        if s.product:
            existing.product = s.product
        if s.version:
            existing.version = s.version
        return existing
    svc = Service(
        host_id=host.id,
        protocol=s.protocol,
        port=s.port,
        state=s.state,
        name=s.name,
        product=s.product,
        version=s.version,
        first_seen=now,
        last_seen=now,
        scan_id=scan_id,
    )
    db.add(svc)
    return svc


def _upsert_endpoint(db: Session, project_id: str, scan_id: str, e: ParsedEndpoint, now: datetime) -> Endpoint:
    existing = db.query(Endpoint).filter_by(project_id=project_id, url=e.url).first()
    if existing:
        existing.last_seen = now
        existing.scan_id = scan_id
        if e.status_code is not None:
            existing.status_code = e.status_code
        if e.content_length is not None:
            existing.content_length = e.content_length
        return existing
    ep = Endpoint(
        project_id=project_id,
        url=e.url,
        path=e.path,
        status_code=e.status_code,
        content_length=e.content_length,
        source_tool=e.source_tool,
        first_seen=now,
        last_seen=now,
        scan_id=scan_id,
    )
    db.add(ep)
    return ep


def run_import(
    db: Session,
    project_id: str,
    target_id: str | None,
    tool: str,
    raw_content: bytes,
) -> Scan:
    """
    Full import pipeline:
    1. Enforce size limit.
    2. Save raw file.
    3. Create Scan(status=running).
    4. Parse.
    5. Upsert hosts/services/endpoints.
    6. Update Scan(status=completed|failed).
    Returns the Scan record.
    """
    if len(raw_content) > MAX_UPLOAD_BYTES:
        raise ValueError(f"Upload exceeds {MAX_UPLOAD_BYTES // (1024*1024)} MB limit")

    raw_path, sha256 = _save_raw(raw_content)

    now = datetime.utcnow()
    scan = Scan(
        project_id=project_id,
        target_id=target_id,
        tool=tool,
        status="running",
        raw_path=raw_path,
        raw_sha256=sha256,
        started_at=now,
    )
    db.add(scan)
    db.flush()  # get scan.id

    try:
        parser = get_parser(raw_content, tool_override=tool)
        if parser is None:
            raise ValueError(f"No parser found for tool '{tool}' and/or content type")

        parse_result: ParseResult = parser.parse(raw_content)

        # Build IP → Host mapping for this import
        now2 = datetime.utcnow()
        ip_to_host: dict[str, Host] = {}
        for h in parse_result.hosts:
            host = _upsert_host(db, project_id, scan.id, h, now2)
            ip_to_host[h.ip] = host

        for s in parse_result.services:
            host = ip_to_host.get(s.ip)
            if host is None:
                # Service references an IP not in hosts list — auto-create host
                host = _upsert_host(db, project_id, scan.id, ParsedHost(ip=s.ip), now2)
                ip_to_host[s.ip] = host
            _upsert_service(db, host, scan.id, s, now2)

        for e in parse_result.endpoints:
            _upsert_endpoint(db, project_id, scan.id, e, now2)

        scan.status = "completed"
        scan.completed_at = datetime.utcnow()
        # Store parse errors in the error field (JSON-serialized list)
        if parse_result.errors:
            import json
            scan.error = json.dumps(parse_result.errors)

    except Exception as exc:
        scan.status = "failed"
        scan.error = str(exc)
        scan.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(scan)
    return scan
