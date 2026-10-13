"""Tests for Findings API and is_interesting toggles."""
from fastapi.testclient import TestClient


def _auth_headers():
    return {"Authorization": "Bearer test_token"}


def _create_project(client: TestClient) -> str:
    resp = client.post(
        "/api/projects",
        json={"name": "Findings Project", "authorized_ack": True},
        headers=_auth_headers(),
    )
    assert resp.status_code == 200
    return resp.json()["id"]


def test_create_and_get_finding(client: TestClient):
    pid = _create_project(client)
    payload = {
        "project_id": pid,
        "title": "Default credentials on admin panel",
        "description": "Admin panel is using admin:admin",
        "severity": "HIGH",
        "status": "OPEN",
        "tags": "auth,admin",
        "links": [
            {"entity_type": "endpoint", "entity_id": "fake-endpoint-id"}
        ],
    }
    resp = client.post("/api/findings", json=payload, headers=_auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == payload["title"]
    assert data["severity"] == "HIGH"
    assert len(data["links"]) == 1

    fid = data["id"]
    get_resp = client.get(f"/api/findings/{fid}", headers=_auth_headers())
    assert get_resp.status_code == 200
    detail = get_resp.json()
    assert detail["id"] == fid
    assert detail["description"] == payload["description"]


def test_list_findings_filtering(client: TestClient):
    pid = _create_project(client)
    client.post(
        "/api/findings",
        json={"project_id": pid, "title": "F1", "severity": "CRITICAL", "status": "OPEN", "tags": "web"},
        headers=_auth_headers(),
    )
    client.post(
        "/api/findings",
        json={"project_id": pid, "title": "F2", "severity": "LOW", "status": "RESOLVED", "tags": "network"},
        headers=_auth_headers(),
    )

    # Filter by severity
    resp = client.get(f"/api/findings?project_id={pid}&severity=CRITICAL", headers=_auth_headers())
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["title"] == "F1"

    # Filter by status
    resp = client.get(f"/api/findings?project_id={pid}&status=RESOLVED", headers=_auth_headers())
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["title"] == "F2"

    # Filter by tag
    resp = client.get(f"/api/findings?project_id={pid}&tag=web", headers=_auth_headers())
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_update_and_delete_finding(client: TestClient):
    pid = _create_project(client)
    f = client.post(
        "/api/findings",
        json={"project_id": pid, "title": "Initial", "severity": "INFO"},
        headers=_auth_headers(),
    ).json()

    # Update
    patch_resp = client.patch(
        f"/api/findings/{f['id']}",
        json={"title": "Updated Title", "severity": "MEDIUM", "status": "CONFIRMED"},
        headers=_auth_headers(),
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["title"] == "Updated Title"
    assert patch_resp.json()["severity"] == "MEDIUM"
    assert patch_resp.json()["status"] == "CONFIRMED"

    # Delete
    del_resp = client.delete(f"/api/findings/{f['id']}", headers=_auth_headers())
    assert del_resp.status_code == 204

    # Confirm 404
    get_resp = client.get(f"/api/findings/{f['id']}", headers=_auth_headers())
    assert get_resp.status_code == 404


def test_finding_links(client: TestClient):
    pid = _create_project(client)
    f = client.post(
        "/api/findings",
        json={"project_id": pid, "title": "Unlinked", "severity": "LOW"},
        headers=_auth_headers(),
    ).json()

    # Add link
    link_resp = client.post(
        f"/api/findings/{f['id']}/links",
        json={"entity_type": "host", "entity_id": "host-123"},
        headers=_auth_headers(),
    )
    assert link_resp.status_code == 200
    link_id = link_resp.json()["id"]

    # Detail shows link
    detail = client.get(f"/api/findings/{f['id']}", headers=_auth_headers()).json()
    assert len(detail["links"]) == 1

    # Remove link
    rem_resp = client.delete(f"/api/findings/{f['id']}/links/{link_id}", headers=_auth_headers())
    assert rem_resp.status_code == 204


def test_toggle_interesting(client: TestClient):
    pid = _create_project(client)
    # Import a sample nmap scan to create host & service
    from pathlib import Path
    import io
    nmap_xml = (Path(__file__).parent / "fixtures" / "nmap_normal.xml").read_bytes()
    client.post(
        "/api/scans/import",
        data={"project_id": pid, "tool": "nmap"},
        files={"file": ("nmap.xml", io.BytesIO(nmap_xml), "text/xml")},
        headers=_auth_headers(),
    )

    hosts = client.get(f"/api/hosts?project_id={pid}", headers=_auth_headers()).json()
    assert len(hosts) > 0
    host = hosts[0]
    assert host["is_interesting"] is False

    # Toggle host
    t_host = client.patch(f"/api/hosts/{host['id']}/interesting", headers=_auth_headers()).json()
    assert t_host["is_interesting"] is True

    # Untoggle host
    t_host2 = client.patch(f"/api/hosts/{host['id']}/interesting", headers=_auth_headers()).json()
    assert t_host2["is_interesting"] is False
