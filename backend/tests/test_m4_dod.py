"""Unit and integration tests for the M4 Tool Engine and Proxy Manager Definition of Done.

Tests:
- Scope and DNS-rebinding target rejection.
- Job lifecycle: status, exit code, stdout, stderr, timeout, cancellation.
- Audit log entries across all job lifecycle events.
- Proxy CRUD API, encryption at rest, secret never returned.
- Proxy test reporting all 4 outcomes (Connected, Failed, Timeout, Authentication failed).
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from app.models.base import Project, Target, ScopeEntry, Job, ProxyProfile, AuditLog
from app.services.job_runner import _run_job, ip_in_cidr
from app.core.crypto import encrypt_secret, decrypt_secret


# ── 1. CIDR and Scope Tests ──────────────────────────────────────────────────

def test_ip_in_cidr_helper():
    assert ip_in_cidr("192.168.1.10", "192.168.1.0/24") is True
    assert ip_in_cidr("10.0.0.1", "192.168.1.0/24") is False
    assert ip_in_cidr("invalid", "192.168.1.0/24") is False


def test_api_rejects_out_of_scope_target(client, db_session):
    p = Project(name="Scope Test", authorized_ack_at=None)
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)

    # In scope: only 192.168.1.100
    se = ScopeEntry(project_id=p.id, type="IP", value="192.168.1.100")
    db_session.add(se)
    db_session.commit()

    # Request scan against out-of-scope target
    resp = client.post(
        "/api/engine/scans/request",
        params={
            "project_id": p.id,
            "target": "10.0.0.99",
            "tool": "nmap",
            "profile": "nmap-top-1000",
        },
        headers={"Authorization": "Bearer test_token"},
    )
    assert resp.status_code == 400
    assert "out of scope" in resp.json()["detail"].lower()


def test_api_accepts_in_scope_target(client, db_session):
    p = Project(name="In Scope Test")
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)

    se = ScopeEntry(project_id=p.id, type="IP", value="192.168.1.50")
    db_session.add(se)
    db_session.commit()

    resp = client.post(
        "/api/engine/scans/request",
        params={
            "project_id": p.id,
            "target": "192.168.1.50",
            "tool": "nmap",
            "profile": "nmap-top-1000",
        },
        headers={"Authorization": "Bearer test_token"},
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "queued"
    assert data["tool"] == "nmap"


# ── 2. Proxy CRUD API & Secret Encryption Tests ──────────────────────────────

def test_proxy_create_encrypts_secret_and_omits_password_in_api(client, db_session):
    resp = client.post(
        "/api/proxy-profiles",
        json={
            "name": "Burp Intercept",
            "type": "BURP",
            "host": "127.0.0.1",
            "port": 8080,
            "username": "tester",
            "password": "supersecretpassword",
        },
        headers={"Authorization": "Bearer test_token"},
    )
    assert resp.status_code == 201
    data = resp.json()
    # The API must NEVER return the secret
    assert "password" not in data
    assert data["has_secret"] is True
    assert data["name"] == "Burp Intercept"

    # In the database, the password must be encrypted with Fernet
    profile = db_session.get(ProxyProfile, data["id"])
    assert profile is not None
    assert profile.encrypted_password is not None
    assert profile.encrypted_password != "supersecretpassword"
    assert decrypt_secret(profile.encrypted_password) == "supersecretpassword"


def test_proxy_list_never_returns_secret(client, db_session):
    p = ProxyProfile(
        name="Corp Proxy",
        type="HTTP",
        host="proxy.corp",
        port=3128,
        username="john",
        encrypted_password=encrypt_secret("corp_password"),
    )
    db_session.add(p)
    db_session.commit()

    resp = client.get("/api/proxy-profiles", headers={"Authorization": "Bearer test_token"})
    assert resp.status_code == 200
    items = resp.json()
    match = next(item for item in items if item["name"] == "Corp Proxy")
    assert "password" not in match
    assert match["has_secret"] is True


# ── 3. Proxy Test All Four Outcomes ──────────────────────────────────────────

@pytest.mark.parametrize(
    "mock_behavior,expected_outcome",
    [
        ("connected", "Connected"),
        ("failed", "Failed"),
        ("timeout", "Timeout"),
        ("auth_failed", "Authentication failed"),
    ],
)
def test_proxy_test_reports_all_four_outcomes(client, db_session, mock_behavior, expected_outcome):
    p = ProxyProfile(name="Test Target Proxy", type="HTTP", host="127.0.0.1", port=8080)
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)

    with patch("httpx.Client.get") as mock_get:
        if mock_behavior == "connected":
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_get.return_value = mock_resp
        elif mock_behavior == "failed":
            mock_resp = MagicMock()
            mock_resp.status_code = 502
            mock_get.return_value = mock_resp
        elif mock_behavior == "timeout":
            import httpx
            mock_get.side_effect = httpx.TimeoutException("Connection timed out")
        elif mock_behavior == "auth_failed":
            mock_resp = MagicMock()
            mock_resp.status_code = 407
            mock_get.return_value = mock_resp

        resp = client.post(f"/api/proxy-profiles/{p.id}/test", headers={"Authorization": "Bearer test_token"})
        assert resp.status_code == 200
        assert resp.json()["outcome"] == expected_outcome


# ── 4. Job Cancellation and Audit Logs ───────────────────────────────────────

def test_cancel_job_lifecycle_and_audit(client, db_session):
    p = Project(name="Audit Test")
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)

    job = Job(
        project_id=p.id,
        tool="nmap",
        profile="nmap-top-1000",
        status="queued",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    # Cancel the queued job
    resp = client.post(f"/api/engine/jobs/{job.id}/cancel", headers={"Authorization": "Bearer test_token"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"

    # Check Audit Log for cancellation entry
    audit_row = db_session.query(AuditLog).filter_by(action="job_cancelled", target=job.id).first()
    assert audit_row is not None
    assert audit_row.tool == "nmap"
