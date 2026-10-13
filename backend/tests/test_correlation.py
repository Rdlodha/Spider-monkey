"""Tests for deterministic correlation engine."""
import io
from pathlib import Path
from fastapi.testclient import TestClient


def _auth_headers():
    return {"Authorization": "Bearer test_token"}


def test_correlation_finds_open_ports_and_paths(client: TestClient):
    # Create project
    p = client.post(
        "/api/projects",
        json={"name": "Correlation Project", "authorized_ack": True},
        headers=_auth_headers(),
    ).json()
    pid = p["id"]

    # Import Nmap fixture (contains ports 22, 80, 443, etc.)
    nmap_xml = (Path(__file__).parent / "fixtures" / "nmap_normal.xml").read_bytes()
    client.post(
        "/api/scans/import",
        data={"project_id": pid, "tool": "nmap"},
        files={"file": ("nmap.xml", io.BytesIO(nmap_xml), "text/xml")},
        headers=_auth_headers(),
    )

    # Import Ferox fixture (contains /admin path)
    ferox_json = (Path(__file__).parent / "fixtures" / "ferox_normal.json").read_bytes()
    client.post(
        "/api/scans/import",
        data={"project_id": pid, "tool": "feroxbuster"},
        files={"file": ("ferox.json", io.BytesIO(ferox_json), "application/json")},
        headers=_auth_headers(),
    )

    # Run correlation
    corr_resp = client.get(f"/api/correlate/{pid}", headers=_auth_headers())
    assert corr_resp.status_code == 200
    suggestions = corr_resp.json()["suggestions"]
    assert len(suggestions) > 0

    # Verify endpoint correlation found /admin
    titles = [s["title"] for s in suggestions]
    assert any("interesting path discovered" in t.lower() and "admin" in t.lower() for t in titles)

    # Verify suggestion attributes
    sample = suggestions[0]
    assert "rule_id" in sample
    assert "severity" in sample
    assert "entity_type" in sample
    assert "entity_id" in sample
    assert "entity_label" in sample
