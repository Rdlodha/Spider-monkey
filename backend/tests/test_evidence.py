"""Tests for Evidence upload, paste, download, and security constraints."""
import io
from fastapi.testclient import TestClient


def _auth_headers():
    return {"Authorization": "Bearer test_token"}


def _setup_finding(client: TestClient) -> str:
    p = client.post(
        "/api/projects",
        json={"name": "Evidence Test Project", "authorized_ack": True},
        headers=_auth_headers(),
    ).json()
    f = client.post(
        "/api/findings",
        json={"project_id": p["id"], "title": "Evidence Finding", "severity": "HIGH"},
        headers=_auth_headers(),
    ).json()
    return f["id"]


def test_upload_valid_evidence_image(client: TestClient):
    fid = _setup_finding(client)
    # Minimal 1x1 PNG bytes
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    resp = client.post(
        f"/api/findings/{fid}/evidence/file",
        files={"file": ("screenshot.png", io.BytesIO(png_bytes), "image/png")},
        headers=_auth_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["kind"] == "screenshot"
    assert data["sha256"] is not None
    assert data["size"] == len(png_bytes)

    # Download
    ev_id = data["id"]
    dl_resp = client.get(f"/api/findings/{fid}/evidence/{ev_id}/download", headers=_auth_headers())
    assert dl_resp.status_code == 200
    assert dl_resp.headers["content-disposition"].startswith("attachment;")
    assert dl_resp.content == png_bytes


def test_reject_dangerous_evidence_files(client: TestClient):
    fid = _setup_finding(client)
    # Attempt HTML file
    resp = client.post(
        f"/api/findings/{fid}/evidence/file",
        files={"file": ("payload.html", io.BytesIO(b"<script>alert(1)</script>"), "text/html")},
        headers=_auth_headers(),
    )
    assert resp.status_code == 400
    assert "not permitted" in resp.json()["detail"].lower()

    # Attempt SVG file
    resp_svg = client.post(
        f"/api/findings/{fid}/evidence/file",
        files={"file": ("vector.svg", io.BytesIO(b"<svg onload=alert(1)>"), "image/svg+xml")},
        headers=_auth_headers(),
    )
    assert resp_svg.status_code == 400


def test_reject_oversized_evidence_file(client: TestClient):
    fid = _setup_finding(client)
    # Exceeds 10 MB limit
    big_bytes = b"0" * (10 * 1024 * 1024 + 1)
    resp = client.post(
        f"/api/findings/{fid}/evidence/file",
        files={"file": ("dump.log", io.BytesIO(big_bytes), "text/plain")},
        headers=_auth_headers(),
    )
    assert resp.status_code == 400
    assert "exceeds" in resp.json()["detail"].lower()


def test_paste_text_evidence(client: TestClient):
    fid = _setup_finding(client)
    sample_text = "GET /admin HTTP/1.1\nHost: target\n\nHTTP/1.1 200 OK\nSet-Cookie: admin=true"
    resp = client.post(
        f"/api/findings/{fid}/evidence/text",
        data={"text": sample_text},
        headers=_auth_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["kind"] == "note"
    assert data["text"] == sample_text

    # Finding detail includes evidence
    f_detail = client.get(f"/api/findings/{fid}", headers=_auth_headers()).json()
    assert len(f_detail["evidence"]) == 1
    assert f_detail["evidence"][0]["text"] == sample_text


def test_delete_evidence(client: TestClient):
    fid = _setup_finding(client)
    ev = client.post(
        f"/api/findings/{fid}/evidence/text",
        data={"text": "Temporary note"},
        headers=_auth_headers(),
    ).json()

    del_resp = client.delete(f"/api/findings/{fid}/evidence/{ev['id']}", headers=_auth_headers())
    assert del_resp.status_code == 204

    f_detail = client.get(f"/api/findings/{fid}", headers=_auth_headers()).json()
    assert len(f_detail["evidence"]) == 0
