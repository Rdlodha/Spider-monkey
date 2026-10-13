"""Tests for Dashboard aggregation statistics."""
import io
from pathlib import Path
from fastapi.testclient import TestClient


def _auth_headers():
    return {"Authorization": "Bearer test_token"}


def test_dashboard_stats_accuracy(client: TestClient):
    # Create project and target
    p = client.post(
        "/api/projects",
        json={"name": "Dashboard Stats Project", "authorized_ack": True},
        headers=_auth_headers(),
    ).json()
    pid = p["id"]
    t = client.post(
        f"/api/projects/{pid}/targets",
        json={"value": "192.168.1.1"},
        headers=_auth_headers(),
    ).json()
    tid = t["id"]

    # Initial stats should be zero
    stats = client.get(f"/api/dashboard/{pid}", headers=_auth_headers()).json()
    assert stats["host_count"] == 0
    assert stats["open_port_count"] == 0
    assert stats["endpoint_count"] == 0
    assert stats["finding_count"] == 0
    assert stats["critical_finding_count"] == 0

    # Import Nmap fixture (creates 2 hosts, multiple open ports)
    nmap_xml = (Path(__file__).parent / "fixtures" / "nmap_normal.xml").read_bytes()
    client.post(
        "/api/scans/import",
        data={"project_id": pid, "tool": "nmap"},
        files={"file": ("nmap.xml", io.BytesIO(nmap_xml), "text/xml")},
        headers=_auth_headers(),
    )

    # Import Ferox fixture (creates 4 endpoints)
    ferox_json = (Path(__file__).parent / "fixtures" / "ferox_normal.json").read_bytes()
    client.post(
        "/api/scans/import",
        data={"project_id": pid, "tool": "feroxbuster"},
        files={"file": ("ferox.json", io.BytesIO(ferox_json), "application/json")},
        headers=_auth_headers(),
    )

    # Add findings
    client.post(
        "/api/findings",
        json={"project_id": pid, "title": "Critical SQLi", "severity": "CRITICAL"},
        headers=_auth_headers(),
    )
    client.post(
        "/api/findings",
        json={"project_id": pid, "title": "Info Disclosure", "severity": "INFO"},
        headers=_auth_headers(),
    )

    # Init and complete a checklist item
    progress_rows = client.get(f"/api/checklists/progress/{tid}", headers=_auth_headers()).json()
    first_item = progress_rows[0]
    client.patch(
        f"/api/checklists/progress/{first_item['id']}",
        json={"state": "COMPLETED"},
        headers=_auth_headers(),
    )

    # Fetch dashboard stats again
    updated = client.get(f"/api/dashboard/{pid}", headers=_auth_headers()).json()
    assert updated["host_count"] == 2
    assert updated["open_port_count"] > 0
    assert updated["endpoint_count"] == 4
    assert updated["finding_count"] == 2
    assert updated["critical_finding_count"] == 1
    assert updated["checklist_completed"] == 1
    assert updated["checklist_total"] == len(progress_rows)
