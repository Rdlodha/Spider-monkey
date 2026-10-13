"""Tests for M5 Reports, Attack Surface Graph, and Audit Log API."""

import pytest
from app.models.base import Project, Target, Host, Service, Endpoint, Finding, FindingLink, Evidence, AuditLog
from app.services.report_service import redact_sensitive, escape_md


def test_redact_sensitive_tokens_and_passwords():
    raw_ev = "Authorization: Bearer my_secret_token_1234567890\npassword='super_secret_password'\nghp_123456789012345678901234567890123456"
    redacted = redact_sensitive(raw_ev)
    assert "my_secret_token_1234567890" not in redacted
    assert "super_secret_password" not in redacted
    assert "12345678901234567890" not in redacted
    assert "[REDACTED]" in redacted


def test_escape_markdown_strips_raw_html():
    malicious = "<script>alert(1)</script> <img src=x onerror=alert(1)>"
    escaped = escape_md(malicious)
    assert "<script>" not in escaped
    assert "&lt;script&gt;" in escaped


def test_markdown_and_pdf_report_endpoints(client, db_session):
    # Setup test project with entities
    p = Project(name="Acme PenTest")
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)

    target = Target(project_id=p.id, value="192.168.1.50")
    db_session.add(target)
    db_session.commit()
    db_session.refresh(target)

    host = Host(project_id=p.id, ip="192.168.1.50", hostname="gateway.acme", first_seen=p.created_at, last_seen=p.created_at)
    db_session.add(host)
    db_session.commit()
    db_session.refresh(host)

    srv = Service(host_id=host.id, protocol="tcp", port=443, state="open", name="https", first_seen=p.created_at, last_seen=p.created_at)
    db_session.add(srv)

    finding = Finding(project_id=p.id, title="Exposed SSL admin portal", severity="HIGH", status="OPEN", description="Admin interface found without MFA")
    db_session.add(finding)
    db_session.commit()

    # 1. Test Markdown endpoint
    md_resp = client.get(f"/api/reports/{p.id}/markdown", headers={"Authorization": "Bearer test_token"})
    assert md_resp.status_code == 200
    md_text = md_resp.text
    assert "# Security Reconnaissance Report: Acme PenTest" in md_text
    assert "192.168.1.50" in md_text
    assert "Exposed SSL admin portal" in md_text

    # 2. Test PDF endpoint
    pdf_resp = client.get(f"/api/reports/{p.id}/pdf", headers={"Authorization": "Bearer test_token"})
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert len(pdf_resp.content) > 1000  # PDF binary output exists
    assert pdf_resp.content.startswith(b"%PDF")


def test_graph_endpoint_structure(client, db_session):
    p = Project(name="Graph Project")
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)

    target = Target(project_id=p.id, value="example.com")
    db_session.add(target)
    db_session.commit()

    resp = client.get(f"/api/graph/{p.id}", headers={"Authorization": "Bearer test_token"})
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data
    assert any(n["type"] == "project" for n in data["nodes"])
    assert any(n["type"] == "target" for n in data["nodes"])


def test_audit_log_endpoint_append_only(client, db_session):
    # Insert audit entry
    log = AuditLog(actor="tester", action="test_action", target="192.168.1.1", result="ok")
    db_session.add(log)
    db_session.commit()

    resp = client.get("/api/audit", headers={"Authorization": "Bearer test_token"})
    assert resp.status_code == 200
    logs = resp.json()
    assert any(l["action"] == "test_action" for l in logs)
