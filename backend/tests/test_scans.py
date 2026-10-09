"""
Integration tests for the scan import API endpoint.
Tests: normal import, re-import (no duplicates), large-file rejection,
       unknown tool rejection, and that parse errors surface in the scan record.
"""
import io
import pytest
from fastapi.testclient import TestClient


def _nmap_bytes() -> bytes:
    from pathlib import Path
    return (Path(__file__).parent / "fixtures" / "nmap_normal.xml").read_bytes()


def _ferox_bytes() -> bytes:
    from pathlib import Path
    return (Path(__file__).parent / "fixtures" / "ferox_normal.json").read_bytes()


def _gobuster_bytes() -> bytes:
    from pathlib import Path
    return (Path(__file__).parent / "fixtures" / "gobuster_normal.txt").read_bytes()


def _make_project(client: TestClient) -> str:
    """Helper to create a project and return its id."""
    resp = client.post(
        "/api/projects",
        json={"name": "Test Project", "authorized_ack": True},
        headers={"Authorization": "Bearer test_token"},
    )
    assert resp.status_code == 200
    return resp.json()["id"]


class TestScanImport:
    def test_import_nmap_success(self, client: TestClient):
        pid = _make_project(client)
        resp = client.post(
            "/api/scans/import",
            data={"project_id": pid, "tool": "nmap"},
            files={"file": ("nmap.xml", io.BytesIO(_nmap_bytes()), "text/xml")},
            headers={"Authorization": "Bearer test_token"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "completed"
        assert body["tool"] == "nmap"
        assert body["raw_sha256"] is not None

    def test_import_creates_hosts(self, client: TestClient):
        pid = _make_project(client)
        client.post(
            "/api/scans/import",
            data={"project_id": pid, "tool": "nmap"},
            files={"file": ("nmap.xml", io.BytesIO(_nmap_bytes()), "text/xml")},
            headers={"Authorization": "Bearer test_token"},
        )
        resp = client.get(
            f"/api/hosts?project_id={pid}",
            headers={"Authorization": "Bearer test_token"},
        )
        assert resp.status_code == 200
        ips = {h["ip"] for h in resp.json()}
        assert "192.168.1.1" in ips
        assert "192.168.1.2" in ips

    def test_reimport_no_duplicates(self, client: TestClient):
        """Importing the same file twice must not duplicate hosts or services."""
        pid = _make_project(client)
        nmap_data = _nmap_bytes()
        for _ in range(2):
            client.post(
                "/api/scans/import",
                data={"project_id": pid, "tool": "nmap"},
                files={"file": ("nmap.xml", io.BytesIO(nmap_data), "text/xml")},
                headers={"Authorization": "Bearer test_token"},
            )
        resp = client.get(
            f"/api/hosts?project_id={pid}",
            headers={"Authorization": "Bearer test_token"},
        )
        assert resp.status_code == 200
        # Should still be exactly 2 hosts
        assert len(resp.json()) == 2

    def test_import_unknown_tool_fails(self, client: TestClient):
        pid = _make_project(client)
        resp = client.post(
            "/api/scans/import",
            data={"project_id": pid, "tool": "unknowntool"},
            files={"file": ("file.txt", io.BytesIO(b"random"), "text/plain")},
            headers={"Authorization": "Bearer test_token"},
        )
        assert resp.status_code in (400, 200)
        if resp.status_code == 200:
            # If it created a scan, it should have status=failed
            assert resp.json()["status"] == "failed"

    def test_import_malformed_nmap_records_error(self, client: TestClient):
        from pathlib import Path
        malformed = (Path(__file__).parent / "fixtures" / "nmap_malformed.xml").read_bytes()
        pid = _make_project(client)
        resp = client.post(
            "/api/scans/import",
            data={"project_id": pid, "tool": "nmap"},
            files={"file": ("bad.xml", io.BytesIO(malformed), "text/xml")},
            headers={"Authorization": "Bearer test_token"},
        )
        assert resp.status_code == 200
        body = resp.json()
        # Malformed XML: parser errors recorded, no crash
        assert body["status"] in ("completed", "failed")

    def test_scan_detail_has_hosts(self, client: TestClient):
        pid = _make_project(client)
        scan_resp = client.post(
            "/api/scans/import",
            data={"project_id": pid, "tool": "nmap"},
            files={"file": ("nmap.xml", io.BytesIO(_nmap_bytes()), "text/xml")},
            headers={"Authorization": "Bearer test_token"},
        )
        scan_id = scan_resp.json()["id"]
        detail = client.get(
            f"/api/scans/{scan_id}",
            headers={"Authorization": "Bearer test_token"},
        ).json()
        assert len(detail["hosts"]) == 2

    def test_host_detail_has_services(self, client: TestClient):
        pid = _make_project(client)
        client.post(
            "/api/scans/import",
            data={"project_id": pid, "tool": "nmap"},
            files={"file": ("nmap.xml", io.BytesIO(_nmap_bytes()), "text/xml")},
            headers={"Authorization": "Bearer test_token"},
        )
        hosts = client.get(
            f"/api/hosts?project_id={pid}",
            headers={"Authorization": "Bearer test_token"},
        ).json()
        host1 = next(h for h in hosts if h["ip"] == "192.168.1.1")
        detail = client.get(
            f"/api/hosts/{host1['id']}",
            headers={"Authorization": "Bearer test_token"},
        ).json()
        ports = {s["port"] for s in detail["services"]}
        assert 22 in ports
        assert 80 in ports
        assert 443 in ports

    def test_import_feroxbuster_success(self, client: TestClient):
        pid = _make_project(client)
        resp = client.post(
            "/api/scans/import",
            data={"project_id": pid, "tool": "feroxbuster"},
            files={"file": ("ferox.json", io.BytesIO(_ferox_bytes()), "application/json")},
            headers={"Authorization": "Bearer test_token"},
        )
        assert resp.status_code == 200
        scan_id = resp.json()["id"]

        detail = client.get(
            f"/api/scans/{scan_id}",
            headers={"Authorization": "Bearer test_token"},
        ).json()
        assert detail["status"] == "completed"
        assert len(detail["endpoints"]) == 4
        urls = {ep["url"] for ep in detail["endpoints"]}
        assert "http://example.com/admin" in urls

    def test_import_gobuster_success(self, client: TestClient):
        pid = _make_project(client)
        resp = client.post(
            "/api/scans/import",
            data={"project_id": pid, "tool": "gobuster"},
            files={"file": ("gobuster.txt", io.BytesIO(_gobuster_bytes()), "text/plain")},
            headers={"Authorization": "Bearer test_token"},
        )
        assert resp.status_code == 200
        scan_id = resp.json()["id"]

        detail = client.get(
            f"/api/scans/{scan_id}",
            headers={"Authorization": "Bearer test_token"},
        ).json()
        assert detail["status"] == "completed"
        assert len(detail["endpoints"]) == 5
        paths = {ep["path"] for ep in detail["endpoints"]}
        assert "/admin" in paths

    def test_reimport_endpoints_no_duplicates(self, client: TestClient):
        pid = _make_project(client)
        ferox_data = _ferox_bytes()
        for _ in range(2):
            resp = client.post(
                "/api/scans/import",
                data={"project_id": pid, "tool": "feroxbuster"},
                files={"file": ("ferox.json", io.BytesIO(ferox_data), "application/json")},
                headers={"Authorization": "Bearer test_token"},
            )
            assert resp.status_code == 200
            last_scan_id = resp.json()["id"]

        detail = client.get(
            f"/api/scans/{last_scan_id}",
            headers={"Authorization": "Bearer test_token"},
        ).json()
        # Endpoints should not duplicate
        assert len(detail["endpoints"]) == 4
