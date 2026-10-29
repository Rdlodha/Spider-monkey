"""
Tests for newly added reconnaissance parsers:
- Subfinder
- Amass
- Httpx
- WhatWeb
- Wappalyzer
"""
import io
import json
import pytest
from fastapi.testclient import TestClient

from app.parsers.subfinder_parser import SubfinderParser
from app.parsers.amass_parser import AmassParser
from app.parsers.httpx_parser import HttpxParser
from app.parsers.whatweb_parser import WhatWebParser
from app.parsers.wappalyzer_parser import WappalyzerParser
from app.parsers.registry import get_parser
from app.services.tool_adapter import get_adapter


def _make_project(client: TestClient) -> str:
    resp = client.post(
        "/api/projects",
        json={"name": "Recon Tool Test", "authorized_ack": True},
        headers={"Authorization": "Bearer test_token"},
    )
    assert resp.status_code == 200
    return resp.json()["id"]


# ── Subfinder Unit & API Tests ───────────────────────────────────────────────

def test_subfinder_parser_unit():
    raw = (
        b'{"host":"api.example.com","input":"example.com","source":"crtsh","ip":"192.168.1.10"}\n'
        b'{"host":"dev.example.com","input":"example.com","source":"hackertarget","ip":"192.168.1.11"}\n'
        b'{"host":"api.example.com","input":"example.com","source":"censys","ip":"192.168.1.10"}\n'
    )
    parser = SubfinderParser()
    assert parser.can_parse(raw)
    result = parser.parse(raw)

    assert len(result.errors) == 0
    # Duplicates should be filtered
    assert len(result.hosts) == 2
    hostnames = {h.hostname for h in result.hosts}
    assert "api.example.com" in hostnames
    assert "dev.example.com" in hostnames


def test_subfinder_api_import(client: TestClient):
    pid = _make_project(client)
    raw = (
        b'{"host":"staging.example.com","input":"example.com","source":"alienvault","ip":"10.0.0.5"}\n'
        b'{"host":"mail.example.com","input":"example.com","source":"censys","ip":"10.0.0.6"}\n'
    )
    resp = client.post(
        "/api/scans/import",
        data={"project_id": pid, "tool": "subfinder"},
        files={"file": ("subfinder.json", io.BytesIO(raw), "application/json")},
        headers={"Authorization": "Bearer test_token"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"

    # Verify hosts were created
    hosts_resp = client.get(f"/api/hosts?project_id={pid}", headers={"Authorization": "Bearer test_token"})
    assert hosts_resp.status_code == 200
    hosts = hosts_resp.json()
    assert len(hosts) >= 2


# ── Amass Unit & API Tests ───────────────────────────────────────────────────

def test_amass_parser_unit():
    raw = (
        b'{"name":"auth.example.com","domain":"example.com","addresses":[{"ip":"192.168.2.1","cidr":"192.168.2.0/24"}],"tag":"cert"}\n'
        b'{"name":"admin.example.com","domain":"example.com","addresses":[{"ip":"192.168.2.2","cidr":"192.168.2.0/24"}],"tag":"dns"}\n'
    )
    parser = AmassParser()
    assert parser.can_parse(raw)
    result = parser.parse(raw)

    assert len(result.errors) == 0
    assert len(result.hosts) == 2
    ips = {h.ip for h in result.hosts}
    assert "192.168.2.1" in ips
    assert "192.168.2.2" in ips


def test_amass_api_import(client: TestClient):
    pid = _make_project(client)
    raw = (
        b'{"name":"portal.target.com","domain":"target.com","addresses":[{"ip":"172.16.0.10"}]}\n'
    )
    resp = client.post(
        "/api/scans/import",
        data={"project_id": pid, "tool": "amass"},
        files={"file": ("amass.json", io.BytesIO(raw), "application/json")},
        headers={"Authorization": "Bearer test_token"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


# ── Httpx Unit & API Tests ───────────────────────────────────────────────────

def test_httpx_parser_unit():
    raw = (
        b'{"url":"https://api.example.com:8443/login","status-code":200,"content-length":1250,"host":"10.0.1.5","port":"8443","scheme":"https","webserver":"nginx/1.22.0","tech":["Nginx","Vue.js"]}\n'
        b'{"url":"http://dashboard.example.com/","status-code":302,"content-length":210,"host":"10.0.1.6","port":"80","scheme":"http","webserver":"Apache/2.4.52","tech":["Apache"]}\n'
    )
    parser = HttpxParser()
    assert parser.can_parse(raw)
    result = parser.parse(raw)

    assert len(result.errors) == 0
    assert len(result.hosts) == 2
    assert len(result.services) == 2
    assert len(result.endpoints) == 2

    # Check parsed service details
    svc = next(s for s in result.services if s.port == 8443)
    assert svc.ip == "10.0.1.5"
    assert svc.product == "nginx"
    assert svc.version == "1.22.0"

    # Check endpoint details
    ep = next(e for e in result.endpoints if "/login" in e.url)
    assert ep.status_code == 200
    assert "httpx:Nginx,Vue.js" in ep.source_tool


def test_httpx_api_import(client: TestClient):
    pid = _make_project(client)
    raw = (
        b'{"url":"http://demo.example.com/api/v1","status-code":200,"content-length":512,"host":"192.168.50.2","port":"80","scheme":"http","webserver":"Werkzeug/2.0.1","tech":["Python","Flask"]}\n'
    )
    resp = client.post(
        "/api/scans/import",
        data={"project_id": pid, "tool": "httpx"},
        files={"file": ("httpx.json", io.BytesIO(raw), "application/json")},
        headers={"Authorization": "Bearer test_token"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"

    # Verify endpoints registered
    ep_resp = client.get(f"/api/endpoints?project_id={pid}", headers={"Authorization": "Bearer test_token"})
    assert ep_resp.status_code == 200
    endpoints = ep_resp.json()
    assert any("/api/v1" in ep["url"] for ep in endpoints)


# ── WhatWeb Unit & API Tests ─────────────────────────────────────────────────

def test_whatweb_parser_unit():
    raw = (
        b'{"target":"http://shop.example.com","http_status":200,"plugins":{"Apache":{"version":["2.4.41"],"string":["2.4.41"]},"PHP":{"version":["7.4.3"]},"WordPress":{"version":["5.8"]}}}\n'
    )
    parser = WhatWebParser()
    assert parser.can_parse(raw)
    result = parser.parse(raw)

    assert len(result.errors) == 0
    assert len(result.hosts) == 1
    assert len(result.services) == 1
    assert len(result.endpoints) == 1

    svc = result.services[0]
    assert svc.product == "Apache"
    assert svc.version == "2.4.41"

    ep = result.endpoints[0]
    assert ep.status_code == 200
    assert "whatweb:" in ep.source_tool
    assert "WordPress" in ep.source_tool


def test_whatweb_api_import(client: TestClient):
    pid = _make_project(client)
    raw = (
        b'{"target":"https://blog.example.com","http_status":200,"plugins":{"Nginx":{"version":["1.18.0"]},"Bootstrap":{}}}\n'
    )
    resp = client.post(
        "/api/scans/import",
        data={"project_id": pid, "tool": "whatweb"},
        files={"file": ("whatweb.json", io.BytesIO(raw), "application/json")},
        headers={"Authorization": "Bearer test_token"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


# ── Wappalyzer Unit & API Tests ──────────────────────────────────────────────

def test_wappalyzer_parser_unit():
    raw = json.dumps({
        "urls": {
            "https://app.example.com/": {"status": 200}
        },
        "technologies": [
            {"slug": "react", "name": "React", "version": "18.2.0"},
            {"slug": "nginx", "name": "Nginx", "version": "1.24.0"},
            {"slug": "tailwind-css", "name": "Tailwind CSS", "version": "3.3.0"}
        ]
    }).encode("utf-8")

    parser = WappalyzerParser()
    assert parser.can_parse(raw)
    result = parser.parse(raw)

    assert len(result.errors) == 0
    assert len(result.hosts) == 1
    assert len(result.services) == 1
    assert len(result.endpoints) == 1

    svc = result.services[0]
    assert svc.product == "Nginx"
    assert svc.version == "1.24.0"

    ep = result.endpoints[0]
    assert "wappalyzer:" in ep.source_tool
    assert "React/18.2.0" in ep.source_tool


def test_wappalyzer_api_import(client: TestClient):
    pid = _make_project(client)
    raw = json.dumps({
        "urls": {
            "http://portal.example.com/": {"status": 200}
        },
        "technologies": [
            {"slug": "vue-js", "name": "Vue.js", "version": "3.2.0"}
        ]
    }).encode("utf-8")

    resp = client.post(
        "/api/scans/import",
        data={"project_id": pid, "tool": "wappalyzer"},
        files={"file": ("wappalyzer.json", io.BytesIO(raw), "application/json")},
        headers={"Authorization": "Bearer test_token"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


# ── Adapters Registry & Validation Tests ──────────────────────────────────────

def test_new_tool_adapters_registered():
    tools = ["subfinder", "amass", "httpx", "whatweb", "wappalyzer"]
    for tool in tools:
        adapter = get_adapter(tool)
        meta = adapter.metadata()
        assert meta["name"] == tool
        assert len(meta["profiles"]) > 0


def test_tool_adapter_command_construction():
    subfinder = get_adapter("subfinder")
    cmd = subfinder.build_command({"target": "example.com", "profile": "subfinder-passive"})
    assert "subfinder" in cmd
    assert "-d" in cmd
    assert "example.com" in cmd

    httpx = get_adapter("httpx")
    cmd = httpx.build_command({"target": "http://example.com", "profile": "httpx-probe"})
    assert "httpx" in cmd
    assert "-u" in cmd
    assert "http://example.com" in cmd

    whatweb = get_adapter("whatweb")
    cmd = whatweb.build_command({"target": "http://example.com", "profile": "whatweb-default"})
    assert "whatweb" in cmd
    assert "http://example.com" in cmd

    wappalyzer = get_adapter("wappalyzer")
    cmd = wappalyzer.build_command({"target": "https://example.com", "profile": "wappalyzer-default"})
    assert "wappalyzer" in cmd
    assert "https://example.com" in cmd
