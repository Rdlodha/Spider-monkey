"""
Findings service: create, update, delete findings and links.
Evidence service: safe upload + text paste.
"""
import hashlib
import os
import secrets
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.orm import Session

from app.models.base import Finding, FindingLink, Evidence
from app.schemas.findings import FindingCreate, FindingUpdate

EVIDENCE_DIR = Path("data/evidence")
MAX_EVIDENCE_BYTES = 10 * 1024 * 1024  # 10 MB

# Only these MIME types are accepted for file evidence uploads.
ALLOWED_MIME = {
    "image/png", "image/jpeg", "image/gif", "image/webp",
    "text/plain", "application/json",
    "application/octet-stream",  # generic binary (log files etc.)
}
BLOCKED_EXTENSIONS = {".html", ".htm", ".svg", ".xml", ".js", ".php"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Finding CRUD ──────────────────────────────────────────────────────────────

def create_finding(db: Session, data: FindingCreate) -> Finding:
    finding = Finding(
        project_id=data.project_id,
        title=data.title,
        description=data.description,
        severity=data.severity.upper(),
        status=data.status.upper(),
        source_tool=data.source_tool,
        source_scan_id=data.source_scan_id,
        notes=data.notes,
        tags=data.tags,
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(finding)
    db.flush()

    for link_data in data.links:
        link = FindingLink(
            finding_id=finding.id,
            entity_type=link_data.entity_type,
            entity_id=link_data.entity_id,
        )
        db.add(link)

    db.commit()
    db.refresh(finding)
    return finding


def update_finding(db: Session, finding: Finding, data: FindingUpdate) -> Finding:
    if data.title is not None:
        finding.title = data.title
    if data.description is not None:
        finding.description = data.description
    if data.severity is not None:
        finding.severity = data.severity.upper()
    if data.status is not None:
        finding.status = data.status.upper()
    if data.notes is not None:
        finding.notes = data.notes
    if data.tags is not None:
        finding.tags = data.tags
    finding.updated_at = _now()
    db.commit()
    db.refresh(finding)
    return finding


def delete_finding(db: Session, finding: Finding) -> None:
    db.delete(finding)
    db.commit()


def add_link(db: Session, finding_id: str, entity_type: str, entity_id: str) -> FindingLink:
    link = FindingLink(finding_id=finding_id, entity_type=entity_type, entity_id=entity_id)
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def remove_link(db: Session, link: FindingLink) -> None:
    db.delete(link)
    db.commit()


# ── Evidence ──────────────────────────────────────────────────────────────────

def _safe_mime(original_filename: str, file_bytes: bytes) -> str:
    """Guess MIME from file header bytes (magic bytes), not the filename."""
    # Simple magic-byte detection for common types
    if file_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if file_bytes[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if file_bytes[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if file_bytes[:4] == b"RIFF" and file_bytes[8:12] == b"WEBP":
        return "image/webp"
    # Try JSON
    stripped = file_bytes[:1024].lstrip()
    if stripped and stripped[0] in (ord("{"), ord("[")):
        return "application/json"
    return "text/plain"


def save_evidence_file(
    db: Session,
    finding_id: str,
    original_filename: str,
    file_bytes: bytes,
) -> Evidence:
    if len(file_bytes) > MAX_EVIDENCE_BYTES:
        raise ValueError(f"Evidence file exceeds {MAX_EVIDENCE_BYTES // (1024*1024)} MB limit")

    # Block dangerous extensions regardless of declared MIME
    suffix = Path(original_filename).suffix.lower()
    if suffix in BLOCKED_EXTENSIONS:
        raise ValueError(f"File type '{suffix}' is not permitted for evidence uploads")

    detected_mime = _safe_mime(original_filename, file_bytes)
    if detected_mime not in ALLOWED_MIME:
        raise ValueError(f"Detected content type '{detected_mime}' is not permitted")

    sha = hashlib.sha256(file_bytes).hexdigest()
    random_name = secrets.token_hex(16) + suffix
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    dest = EVIDENCE_DIR / random_name
    dest.write_bytes(file_bytes)

    evidence = Evidence(
        finding_id=finding_id,
        kind="tool_output" if detected_mime in ("application/json", "text/plain") else "screenshot",
        path=str(dest),
        sha256=sha,
        size=len(file_bytes),
        original_filename=original_filename,
        mime_type=detected_mime,
        created_at=_now(),
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence


def save_evidence_text(db: Session, finding_id: str, text: str) -> Evidence:
    evidence = Evidence(
        finding_id=finding_id,
        kind="note",
        text=text,
        created_at=_now(),
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence


def delete_evidence(db: Session, evidence: Evidence) -> None:
    if evidence.path:
        try:
            Path(evidence.path).unlink(missing_ok=True)
        except Exception:
            pass
    db.delete(evidence)
    db.commit()
