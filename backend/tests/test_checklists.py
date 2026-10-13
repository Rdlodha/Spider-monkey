"""Tests for Checklist templates and per-target progress persistence."""
from fastapi.testclient import TestClient


def _auth_headers():
    return {"Authorization": "Bearer test_token"}


def _setup_target(client: TestClient) -> tuple[str, str]:
    p = client.post(
        "/api/projects",
        json={"name": "Checklist Project", "authorized_ack": True},
        headers=_auth_headers(),
    ).json()
    t = client.post(
        f"/api/projects/{p['id']}/targets",
        json={"value": "https://example.com"},
        headers=_auth_headers(),
    ).json()
    return p["id"], t["id"]


def test_list_templates(client: TestClient):
    resp = client.get("/api/checklists/templates", headers=_auth_headers())
    assert resp.status_code == 200
    templates = resp.json()
    names = {tpl["name"] for tpl in templates}
    assert "Web Application" in names
    assert "Network / Infrastructure" in names
    assert "Database Assessment" in names

    # Items exist on template
    web_tpl = next(tpl for tpl in templates if tpl["name"] == "Web Application")
    assert len(web_tpl["items"]) > 0


def test_target_checklist_progress_lifecycle(client: TestClient):
    _, tid = _setup_target(client)

    # Initial get creates NOT_STARTED rows for all template items
    prog_resp = client.get(f"/api/checklists/progress/{tid}", headers=_auth_headers())
    assert prog_resp.status_code == 200
    rows = prog_resp.json()
    assert len(rows) > 0
    assert all(r["state"] == "NOT_STARTED" for r in rows)

    first_item = rows[0]
    prog_id = first_item["id"]

    # Update item to COMPLETED with a note
    update_resp = client.patch(
        f"/api/checklists/progress/{prog_id}",
        json={"state": "COMPLETED", "note": "Checked robots.txt, nothing sensitive"},
        headers=_auth_headers(),
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["state"] == "COMPLETED"
    assert updated["note"] == "Checked robots.txt, nothing sensitive"

    # Reload / re-fetch progress - ensures state persisted across requests
    reload_resp = client.get(f"/api/checklists/progress/{tid}", headers=_auth_headers())
    assert reload_resp.status_code == 200
    reloaded_item = next(r for r in reload_resp.json() if r["id"] == prog_id)
    assert reloaded_item["state"] == "COMPLETED"
    assert reloaded_item["note"] == "Checked robots.txt, nothing sensitive"


def test_invalid_progress_state_rejected(client: TestClient):
    _, tid = _setup_target(client)
    rows = client.get(f"/api/checklists/progress/{tid}", headers=_auth_headers()).json()
    prog_id = rows[0]["id"]

    resp = client.patch(
        f"/api/checklists/progress/{prog_id}",
        json={"state": "INVALID_STATE"},
        headers=_auth_headers(),
    )
    assert resp.status_code == 400
