"""
Checklist service: seed templates and manage per-target progress.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.base import (
    ChecklistTemplate,
    ChecklistTemplateItem,
    ChecklistProgress,
    Target,
)

# ── Seed data ─────────────────────────────────────────────────────────────────

_TEMPLATES = [
    {
        "name": "Web Application",
        "description": "Standard web application penetration test checklist.",
        "items": [
            ("Reconnaissance", "Identify technologies (server, framework, language)", 10),
            ("Reconnaissance", "Check HTTP response headers for disclosure", 20),
            ("Reconnaissance", "Enumerate directories and files", 30),
            ("Reconnaissance", "Check robots.txt and sitemap.xml", 40),
            ("Reconnaissance", "Find exposed .git / .env / backup files", 50),
            ("Authentication", "Test login page for default credentials", 60),
            ("Authentication", "Test for username enumeration", 70),
            ("Authentication", "Test for account lockout policy", 80),
            ("Authentication", "Test password reset flow for weaknesses", 90),
            ("Authorization", "Test for IDOR on user-specific resources", 100),
            ("Authorization", "Test horizontal privilege escalation", 110),
            ("Authorization", "Test vertical privilege escalation (admin functions)", 120),
            ("Injection", "Test all inputs for SQL injection", 130),
            ("Injection", "Test all inputs for XSS (reflected and stored)", 140),
            ("Injection", "Test file upload for path traversal / SSRF", 150),
            ("Configuration", "Check for interesting HTTP status codes (403, 500)", 160),
            ("Configuration", "Verify Content Security Policy headers", 170),
            ("Configuration", "Check for open API documentation (/swagger, /graphql)", 180),
            ("Configuration", "Test CORS policy for overly permissive origins", 190),
            ("Session", "Verify session tokens are random and HTTP-only", 200),
            ("Session", "Test for CSRF on state-changing requests", 210),
        ],
    },
    {
        "name": "Network / Infrastructure",
        "description": "Network and infrastructure security checklist.",
        "items": [
            ("Discovery", "Identify all live hosts in scope", 10),
            ("Discovery", "Map all open ports per host", 20),
            ("Discovery", "Identify running services and versions", 30),
            ("Discovery", "Check for unusual or high-numbered ports", 40),
            ("Remote Access", "Check for SSH default credentials", 50),
            ("Remote Access", "Check for RDP exposure (port 3389)", 60),
            ("Remote Access", "Check for VNC exposure (port 5900)", 70),
            ("Remote Access", "Check for Telnet (port 23)", 80),
            ("Databases", "Check for exposed MySQL (3306)", 90),
            ("Databases", "Check for exposed PostgreSQL (5432)", 100),
            ("Databases", "Check for exposed MongoDB (27017) without auth", 110),
            ("Databases", "Check for exposed Redis (6379) without auth", 120),
            ("Databases", "Check for exposed MSSQL (1433)", 130),
            ("File Services", "Check for anonymous FTP (port 21)", 140),
            ("File Services", "Check for open SMB shares (port 445)", 150),
            ("Vulnerabilities", "Check services for known CVEs via version", 160),
            ("Vulnerabilities", "Check for EternalBlue / SMBv1 vulnerability", 170),
        ],
    },
    {
        "name": "Database Assessment",
        "description": "Database-focused security checklist.",
        "items": [
            ("Access", "Verify database is not exposed externally", 10),
            ("Access", "Confirm strong authentication is enforced", 20),
            ("Access", "List all database users and their privileges", 30),
            ("Access", "Identify accounts with excessive privileges", 40),
            ("Access", "Check for default or blank passwords", 50),
            ("Data", "Locate tables containing sensitive/PII data", 60),
            ("Data", "Check encryption at rest configuration", 70),
            ("Data", "Review backup strategy and backup file exposure", 80),
            ("Audit", "Verify audit logging is enabled", 90),
            ("Audit", "Confirm logs are shipped to a SIEM / external system", 100),
            ("Configuration", "Check database version for known vulnerabilities", 110),
            ("Configuration", "Review stored procedures for injection risks", 120),
            ("Configuration", "Check for xp_cmdshell or equivalent enabled (MSSQL)", 130),
        ],
    },
]


def seed_templates(db: Session) -> None:
    """Idempotent: only inserts templates that don't already exist by name."""
    for tpl_data in _TEMPLATES:
        exists = db.query(ChecklistTemplate).filter_by(name=tpl_data["name"]).first()
        if exists:
            continue
        tpl = ChecklistTemplate(
            id=str(uuid.uuid4()),
            name=tpl_data["name"],
            description=tpl_data["description"],
        )
        db.add(tpl)
        db.flush()
        for section, title, sort_order in tpl_data["items"]:
            item = ChecklistTemplateItem(
                id=str(uuid.uuid4()),
                template_id=tpl.id,
                section=section,
                title=title,
                sort_order=sort_order,
            )
            db.add(item)
    db.commit()


def get_or_create_progress_for_target(
    db: Session, target: Target
) -> list[ChecklistProgress]:
    """
    Ensure every ChecklistTemplateItem has a ChecklistProgress row for this target.
    New rows are initialised to NOT_STARTED.
    Existing rows are left untouched (editing a template later does not overwrite old progress).
    Returns all progress rows for the target.
    """
    all_items = db.query(ChecklistTemplateItem).all()
    existing_ids = {
        p.template_item_id
        for p in db.query(ChecklistProgress).filter_by(target_id=target.id).all()
    }
    now = datetime.now(timezone.utc)
    for item in all_items:
        if item.id not in existing_ids:
            db.add(
                ChecklistProgress(
                    id=str(uuid.uuid4()),
                    target_id=target.id,
                    template_item_id=item.id,
                    state="NOT_STARTED",
                    updated_at=now,
                )
            )
    db.commit()
    return (
        db.query(ChecklistProgress)
        .filter_by(target_id=target.id)
        .all()
    )


def update_progress(
    db: Session,
    progress: ChecklistProgress,
    state: str,
    note: str | None,
) -> ChecklistProgress:
    progress.state = state.upper()
    if note is not None:
        progress.note = note
    progress.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(progress)
    return progress
