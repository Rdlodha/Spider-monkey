"""
seed_demo.py — Populate ReconForge with realistic demo data for portfolio/demo purposes.

Usage:
    cd backend
    python ../scripts/seed_demo.py

This creates:
  - 1 demo project: "DVWA Lab Assessment"
  - 3 targets (scope entries)
  - 3 hosts with services
  - 8 endpoints
  - 5 findings (CRITICAL/HIGH/MEDIUM/LOW/INFO)
  - 3 evidence entries
  - Checklist progress entries

Safe to run multiple times — uses upsert-style logic (skips if project already exists).
"""

import sys
import os
import uuid
from datetime import datetime, timezone

# Make sure we can import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.base import (
    Project, Target, Host, Service, Endpoint,
    Finding, FindingLink, Evidence,
    ChecklistTemplate, ChecklistTemplateItem, ChecklistProgress,
    ScopeEntry, AuditLog
)

NOW = datetime.now(timezone.utc)

def upsert_project(db: Session) -> Project:
    existing = db.query(Project).filter(Project.name == "DVWA Lab Assessment").first()
    if existing:
        print(f"  Project already exists: {existing.id}")
        return existing

    proj = Project(
        id=str(uuid.uuid4()),
        name="DVWA Lab Assessment",
        authorized_ack_at=NOW,
    )
    db.add(proj)
    db.flush()
    print(f"  Created project: {proj.id}")
    return proj


def seed_scope(db: Session, project_id: str) -> list[ScopeEntry]:
    entries = []
    for val, typ in [("192.168.100.0/24", "network"), ("http://localhost:3000", "url"), ("http://localhost:8080", "url")]:
        if not db.query(ScopeEntry).filter(ScopeEntry.project_id == project_id, ScopeEntry.value == val).first():
            se = ScopeEntry(id=str(uuid.uuid4()), project_id=project_id, value=val, type=typ)
            db.add(se)
            entries.append(se)
    db.flush()
    print(f"  Seeded {len(entries)} scope entries")
    return entries


def seed_targets(db: Session, project_id: str) -> list[Target]:
    targets = []
    for val in ["192.168.100.10", "localhost:3000", "localhost:8080"]:
        existing = db.query(Target).filter(Target.project_id == project_id, Target.value == val).first()
        if not existing:
            t = Target(id=str(uuid.uuid4()), project_id=project_id, value=val)
            db.add(t)
            targets.append(t)
        else:
            targets.append(existing)
    db.flush()
    print(f"  Seeded {len(targets)} targets")
    return targets


def seed_hosts_services(db: Session, project_id: str) -> list[Host]:
    hosts_data = [
        {
            "ip": "192.168.100.10", "hostname": "dvwa.lab",
            "services": [
                {"port": 80,   "protocol": "tcp", "name": "http",    "product": "Apache httpd",  "version": "2.4.51", "is_interesting": True},
                {"port": 3306, "protocol": "tcp", "name": "mysql",   "product": "MySQL",          "version": "5.7.36", "is_interesting": True},
                {"port": 22,   "protocol": "tcp", "name": "ssh",     "product": "OpenSSH",        "version": "8.2p1",  "is_interesting": False},
            ]
        },
        {
            "ip": "192.168.100.11", "hostname": "juiceshop.lab",
            "services": [
                {"port": 3000, "protocol": "tcp", "name": "http",    "product": "Node.js/Express","version": "18.x",   "is_interesting": True},
                {"port": 443,  "protocol": "tcp", "name": "https",   "product": "nginx",          "version": "1.21.3", "is_interesting": False},
            ]
        },
        {
            "ip": "192.168.100.1", "hostname": "gateway.lab",
            "services": [
                {"port": 80,   "protocol": "tcp", "name": "http",    "product": "MikroTik RouterOS", "version": "6.49", "is_interesting": True},
                {"port": 8291, "protocol": "tcp", "name": "winbox",  "product": "MikroTik Winbox","version": "",       "is_interesting": True},
            ]
        },
    ]

    created_hosts = []
    for hd in hosts_data:
        existing = db.query(Host).filter(Host.project_id == project_id, Host.ip == hd["ip"]).first()
        if existing:
            created_hosts.append(existing)
            continue
        h = Host(
            id=str(uuid.uuid4()), project_id=project_id,
            ip=hd["ip"], hostname=hd["hostname"],
            is_interesting=any(s["is_interesting"] for s in hd["services"]),
            first_seen=NOW, last_seen=NOW,
        )
        db.add(h)
        db.flush()
        for sd in hd["services"]:
            s = Service(
                id=str(uuid.uuid4()), host_id=h.id,
                protocol=sd["protocol"], port=sd["port"],
                state="open", name=sd["name"],
                product=sd["product"], version=sd["version"],
                is_interesting=sd["is_interesting"],
                first_seen=NOW, last_seen=NOW,
            )
            db.add(s)
        created_hosts.append(h)
    db.flush()
    print(f"  Seeded {len(created_hosts)} hosts")
    return created_hosts


def seed_endpoints(db: Session, project_id: str, hosts: list[Host]) -> list[Endpoint]:
    dvwa_host = next((h for h in hosts if h.ip == "192.168.100.10"), None)
    juice_host = next((h for h in hosts if h.ip == "192.168.100.11"), None)

    endpoints_data = [
        {"url": "http://192.168.100.10/dvwa/login.php",           "path": "/dvwa/login.php",        "status_code": 200, "host": dvwa_host,  "is_interesting": False},
        {"url": "http://192.168.100.10/dvwa/vulnerabilities/sqli/","path": "/dvwa/vulnerabilities/sqli/","status_code": 200,"host": dvwa_host, "is_interesting": True},
        {"url": "http://192.168.100.10/dvwa/vulnerabilities/xss_r/","path": "/dvwa/vulnerabilities/xss_r/","status_code": 200,"host": dvwa_host,"is_interesting": True},
        {"url": "http://192.168.100.10/phpmyadmin/",               "path": "/phpmyadmin/",           "status_code": 200, "host": dvwa_host,  "is_interesting": True},
        {"url": "http://192.168.100.10/dvwa/setup.php",            "path": "/dvwa/setup.php",        "status_code": 200, "host": dvwa_host,  "is_interesting": True},
        {"url": "http://192.168.100.11:3000/api/Users/",           "path": "/api/Users/",            "status_code": 200, "host": juice_host, "is_interesting": True},
        {"url": "http://192.168.100.11:3000/#/login",              "path": "/#/login",               "status_code": 200, "host": juice_host, "is_interesting": False},
        {"url": "http://192.168.100.11:3000/api/Products",         "path": "/api/Products",          "status_code": 200, "host": juice_host, "is_interesting": False},
    ]

    created = []
    for ep_data in endpoints_data:
        url = ep_data["url"]
        existing = db.query(Endpoint).filter(Endpoint.project_id == project_id, Endpoint.url == url).first()
        if existing:
            created.append(existing)
            continue
        ep = Endpoint(
            id=str(uuid.uuid4()), project_id=project_id,
            host_id=ep_data["host"].id if ep_data["host"] else None,
            url=url, path=ep_data["path"],
            status_code=ep_data["status_code"],
            is_interesting=ep_data["is_interesting"],
            source_tool="feroxbuster",
            first_seen=NOW, last_seen=NOW,
        )
        db.add(ep)
        created.append(ep)
    db.flush()
    print(f"  Seeded {len(created)} endpoints")
    return created


def seed_findings(db: Session, project_id: str, hosts: list[Host], endpoints: list[Endpoint]) -> list[Finding]:
    dvwa_host = next((h for h in hosts if h.ip == "192.168.100.10"), None)
    juice_host = next((h for h in hosts if h.ip == "192.168.100.11"), None)
    sqli_ep = next((e for e in endpoints if "sqli" in e.url), None)
    phpmyadmin_ep = next((e for e in endpoints if "phpmyadmin" in e.url), None)
    users_ep = next((e for e in endpoints if "Users" in e.url), None)

    findings_data = [
        {
            "title": "SQL Injection — DVWA Login Bypass",
            "severity": "CRITICAL", "status": "CONFIRMED",
            "description": "Classic SQL injection in the `id` parameter of `dvwa/vulnerabilities/sqli/`. Payload `' OR '1'='1` returns all users from the database. Full database dump achievable via UNION-based injection.",
            "source_tool": "manual",
            "tags": "sqli,owasp-a03,authentication-bypass",
            "notes": "Tested with sqlmap and manual payload. Full DB access confirmed.",
            "entity": sqli_ep,
            "entity_type": "endpoint",
        },
        {
            "title": "phpMyAdmin Exposed Without Authentication",
            "severity": "HIGH", "status": "CONFIRMED",
            "description": "phpMyAdmin administrative interface is accessible at `/phpmyadmin/` without any additional authentication. Combined with a weak MySQL root password, this allows full database control.",
            "source_tool": "feroxbuster",
            "tags": "exposure,misconfig,owasp-a05",
            "notes": "Default credentials admin:admin work. Change immediately.",
            "entity": phpmyadmin_ep,
            "entity_type": "endpoint",
        },
        {
            "title": "Juice Shop — User Enumeration via /api/Users/",
            "severity": "MEDIUM", "status": "OPEN",
            "description": "The `/api/Users/` endpoint returns a full list of all registered users including email addresses, usernames and hashed passwords. No authentication is required for this endpoint.",
            "source_tool": "manual",
            "tags": "api,user-enumeration,owasp-a01",
            "notes": "Response includes bcrypt hashes — offline cracking feasible.",
            "entity": users_ep,
            "entity_type": "endpoint",
        },
        {
            "title": "MySQL 5.7 — Known CVE (End of Life)",
            "severity": "LOW", "status": "OPEN",
            "description": "MySQL 5.7.36 is running on port 3306 and has reached End of Life (October 2023). Several unpatched CVEs exist including CVE-2023-22005. Upgrade to MySQL 8.x is required.",
            "source_tool": "nmap",
            "tags": "eol,cve,mysql",
            "notes": "Nmap service version scan identified MySQL 5.7.36.",
            "entity": dvwa_host,
            "entity_type": "host",
        },
        {
            "title": "SSH Server Banner Disclosure",
            "severity": "INFO", "status": "FALSE_POSITIVE",
            "description": "SSH service at port 22 reveals version string `OpenSSH_8.2p1 Ubuntu-4ubuntu0.5`. This is standard behaviour and the version is not vulnerable. Marked as false positive.",
            "source_tool": "nmap",
            "tags": "info,ssh,banner",
            "notes": "Version is fully patched. No action required.",
            "entity": dvwa_host,
            "entity_type": "host",
        },
    ]

    created = []
    for fd in findings_data:
        existing = db.query(Finding).filter(Finding.project_id == project_id, Finding.title == fd["title"]).first()
        if existing:
            created.append(existing)
            continue
        f = Finding(
            id=str(uuid.uuid4()), project_id=project_id,
            title=fd["title"], severity=fd["severity"], status=fd["status"],
            description=fd["description"], source_tool=fd["source_tool"],
            tags=fd["tags"], notes=fd["notes"],
        )
        db.add(f)
        db.flush()
        # Link finding to entity
        entity = fd.get("entity")
        if entity:
            link = FindingLink(
                id=str(uuid.uuid4()), finding_id=f.id,
                entity_type=fd["entity_type"], entity_id=entity.id,
            )
            db.add(link)
        created.append(f)
    db.flush()
    print(f"  Seeded {len(created)} findings")
    return created


def seed_evidence(db: Session, findings: list[Finding]) -> None:
    critical_finding = next((f for f in findings if f.severity == "CRITICAL"), None)
    high_finding = next((f for f in findings if f.severity == "HIGH"), None)
    if not critical_finding or not high_finding:
        return

    evidence_data = [
        {
            "finding_id": critical_finding.id,
            "kind": "tool_output",
            "text": (
                "$ sqlmap -u 'http://192.168.100.10/dvwa/vulnerabilities/sqli/?id=1&Submit=Submit' "
                "--cookie='PHPSESSID=abc123; security=low' --dbs\n\n"
                "[INFO] the back-end DBMS is MySQL\n"
                "[INFO] fetching database names\n"
                "available databases [3]:\n"
                "[*] dvwa\n[*] information_schema\n[*] mysql\n"
            ),
        },
        {
            "finding_id": critical_finding.id,
            "kind": "request_response",
            "text": (
                "GET /dvwa/vulnerabilities/sqli/?id=' OR '1'='1&Submit=Submit HTTP/1.1\n"
                "Host: 192.168.100.10\nCookie: PHPSESSID=abc123; security=low\n\n"
                "HTTP/1.1 200 OK\nContent-Type: text/html\n\n"
                "<pre>ID: ' OR '1'='1\nFirst name: admin\nSurname: admin\n"
                "ID: ' OR '1'='1\nFirst name: Gordon\nSurname: Brown\n...</pre>"
            ),
        },
        {
            "finding_id": high_finding.id,
            "kind": "note",
            "text": "Confirmed via browser: navigated to http://192.168.100.10/phpmyadmin/ — presented with phpMyAdmin 5.1.1 dashboard immediately. No login prompt. Full SQL execution capability verified.",
        },
    ]

    for ev_data in evidence_data:
        existing = db.query(Evidence).filter(
            Evidence.finding_id == ev_data["finding_id"],
            Evidence.kind == ev_data["kind"],
        ).first()
        if not existing:
            ev = Evidence(
                id=str(uuid.uuid4()),
                finding_id=ev_data["finding_id"],
                kind=ev_data["kind"],
                text=ev_data["text"],
            )
            db.add(ev)
    db.flush()
    print("  Seeded evidence entries")


def seed_checklist_progress(db: Session, project_id: str) -> None:
    targets = db.query(Target).filter(Target.project_id == project_id).all()
    if not targets:
        return
    target = targets[0]

    template = db.query(ChecklistTemplate).first()
    if not template:
        print("  No checklist template found — skipping checklist progress seed")
        return

    items = db.query(ChecklistTemplateItem).filter(ChecklistTemplateItem.template_id == template.id).limit(10).all()
    states = ["COMPLETED", "COMPLETED", "COMPLETED", "COMPLETED", "IN_PROGRESS", "IN_PROGRESS", "NOT_STARTED", "NOT_STARTED", "NOT_STARTED", "NOT_APPLICABLE"]

    for i, item in enumerate(items):
        existing = db.query(ChecklistProgress).filter(
            ChecklistProgress.target_id == target.id,
            ChecklistProgress.template_item_id == item.id,
        ).first()
        if not existing:
            cp = ChecklistProgress(
                id=str(uuid.uuid4()),
                target_id=target.id,
                template_item_id=item.id,
                state=states[i % len(states)],
                note="Demo data — seeded by seed_demo.py" if states[i % len(states)] == "COMPLETED" else None,
            )
            db.add(cp)
    db.flush()
    print("  Seeded checklist progress")


def seed_audit_entries(db: Session, project_id: str) -> None:
    entries = [
        {"action": "create_project",  "target": project_id,    "result": "ok"},
        {"action": "import_scan",     "target": project_id,    "tool": "nmap",        "result": "ok"},
        {"action": "import_scan",     "target": project_id,    "tool": "feroxbuster", "result": "ok"},
        {"action": "create_finding",  "target": project_id,    "result": "ok"},
        {"action": "update_finding",  "target": project_id,    "result": "ok"},
    ]
    for e in entries:
        al = AuditLog(
            id=str(uuid.uuid4()),
            actor="local",
            action=e["action"],
            target=e.get("target"),
            tool=e.get("tool"),
            result=e.get("result", "ok"),
        )
        db.add(al)
    db.flush()
    print("  Seeded audit log entries")


def main():
    print("=== ReconForge Demo Seed ===")
    engine = create_engine(settings.database_url)
    with Session(engine) as db:
        project = upsert_project(db)
        seed_scope(db, project.id)
        targets = seed_targets(db, project.id)
        hosts = seed_hosts_services(db, project.id)
        endpoints = seed_endpoints(db, project.id, hosts)
        findings = seed_findings(db, project.id, hosts, endpoints)
        seed_evidence(db, findings)
        seed_checklist_progress(db, project.id)
        seed_audit_entries(db, project.id)
        db.commit()
    print("\n✅ Demo data seeded successfully!")
    print(f"   Project: 'DVWA Lab Assessment'")
    print(f"   Run 'npm run dev' + uvicorn and open http://localhost:5173 to see the dashboard.")


if __name__ == "__main__":
    main()
