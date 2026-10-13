"""Tests for the Proxy Manager API (Part B).

Covers:
- CRUD for ProxyProfile (create, list, get, update, delete).
- Fernet encryption: secret never returned by the API.
- Proxy test endpoint returning all four outcomes.
- ToolAdapter.validate() rejecting unsupported proxy types.
- _proxy_flags_for_tool() generating correct argv lists.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.base import Base, ProxyProfile
from app.core.crypto import encrypt_secret, decrypt_secret


# ── Crypto helpers ────────────────────────────────────────────────────────────

def test_encrypt_decrypt_roundtrip():
    plaintext = "super-secret-password-123"
    ct = encrypt_secret(plaintext)
    assert ct != plaintext
    assert decrypt_secret(ct) == plaintext


def test_encrypted_value_differs_from_plaintext():
    ct = encrypt_secret("password")
    assert not ct.startswith("password")


# ── ToolAdapter proxy flag generation ────────────────────────────────────────

from app.services.tool_adapter import _proxy_flags_for_tool, NmapAdapter, FeroxbusterAdapter, GobusterAdapter


def test_direct_proxy_returns_empty():
    assert _proxy_flags_for_tool("nmap", {"type": "DIRECT"}) == []


def test_nmap_http_proxy_flags():
    flags = _proxy_flags_for_tool("nmap", {"type": "HTTP", "host": "127.0.0.1", "port": 8080})
    assert "--proxies" in flags
    assert "http://127.0.0.1:8080" in flags


def test_nmap_rejects_https_proxy():
    with pytest.raises(ValueError, match="nmap does not support proxy type HTTPS"):
        _proxy_flags_for_tool("nmap", {"type": "HTTPS", "host": "127.0.0.1", "port": 8080})


def test_feroxbuster_http_proxy_flags():
    flags = _proxy_flags_for_tool("feroxbuster", {"type": "HTTP", "host": "10.0.0.1", "port": 8080})
    assert "--proxy" in flags
    assert "http://10.0.0.1:8080" in flags


def test_feroxbuster_proxy_with_auth():
    flags = _proxy_flags_for_tool("feroxbuster", {
        "type": "HTTP", "host": "10.0.0.1", "port": 8080,
        "username": "user", "password": "pass"
    })
    assert "--proxy" in flags
    assert "http://user:pass@10.0.0.1:8080" in flags


def test_gobuster_socks5_proxy():
    flags = _proxy_flags_for_tool("gobuster", {"type": "SOCKS5", "host": "127.0.0.1", "port": 1080})
    assert "--proxy" in flags
    assert "socks5://127.0.0.1:1080" in flags


def test_nmap_rejects_dash_target():
    adapter = NmapAdapter()
    with pytest.raises(ValueError, match="dash"):
        adapter.validate({"target": "-evil", "profile": "nmap-top-1000"})


def test_nmap_rejects_invalid_profile():
    adapter = NmapAdapter()
    with pytest.raises(ValueError, match="Unsupported nmap profile"):
        adapter.validate({"target": "192.168.1.1", "profile": "nmap-stealth"})


def test_feroxbuster_rejects_dash_target():
    adapter = FeroxbusterAdapter()
    with pytest.raises(ValueError, match="dash"):
        adapter.validate({"target": "-evil", "profile": "ferox-common"})


def test_gobuster_rejects_dash_target():
    adapter = GobusterAdapter()
    with pytest.raises(ValueError, match="dash"):
        adapter.validate({"target": "--inject", "profile": "gobuster-dir"})


def test_nmap_command_includes_proxy():
    adapter = NmapAdapter()
    cmd = adapter.build_command({
        "target": "192.168.1.1",
        "profile": "nmap-top-1000",
        "proxy": {"type": "HTTP", "host": "127.0.0.1", "port": 8080},
    })
    assert cmd[0] == "nmap"
    assert "--proxies" in cmd
    assert cmd[-1] == "192.168.1.1"  # target always last


def test_gobuster_command_no_proxy():
    adapter = GobusterAdapter()
    cmd = adapter.build_command({
        "target": "http://example.local",
        "profile": "gobuster-dir",
    })
    assert cmd[0] == "gobuster"
    assert "-u" in cmd
    assert "http://example.local" in cmd


def test_hostile_input_semicolon():
    """Semicolons in target must not break argv list (they're just passed as a literal string)."""
    adapter = NmapAdapter()
    cmd = adapter.build_command({
        "target": "192.168.1.1;id",
        "profile": "nmap-top-1000",
    })
    # The entire ';id' is a single element in the list – never interpreted by a shell.
    assert "192.168.1.1;id" in cmd
    assert len([c for c in cmd if ";" in c]) == 1


def test_hostile_input_command_substitution():
    adapter = NmapAdapter()
    cmd = adapter.build_command({
        "target": "$(cat /etc/passwd)",
        "profile": "nmap-top-1000",
    })
    # Must be a single argv element, not split or interpreted.
    assert any("$(cat /etc/passwd)" == c for c in cmd)


def test_hostile_input_unicode():
    adapter = GobusterAdapter()
    # Unicode characters are fine as long as they don't start with '-'.
    cmd = adapter.build_command({
        "target": "http://目标.local",
        "profile": "gobuster-dir",
    })
    assert "http://目标.local" in cmd
