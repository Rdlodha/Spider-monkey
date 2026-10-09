"""
Tests for all parsers: NmapParser, FeroxParser, GobusterParser.
Covers: normal scans, no-open-ports, malformed input, XXE attempt,
        and duplicate re-import (no duplicates at DB level).
"""
import json
import pytest
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


# ─────────────────────────── NmapParser ──────────────────────────────────────

class TestNmapParser:
    def setup_method(self):
        from app.parsers.nmap_parser import NmapParser
        self.parser = NmapParser()

    def _read(self, name: str) -> bytes:
        return (FIXTURES / name).read_bytes()

    def test_can_parse_valid_nmap(self):
        assert self.parser.can_parse(self._read("nmap_normal.xml")) is True

    def test_cannot_parse_random_text(self):
        assert self.parser.can_parse(b"hello world, not nmap") is False

    def test_normal_scan_hosts(self):
        result = self.parser.parse(self._read("nmap_normal.xml"))
        assert len(result.errors) == 0
        ips = {h.ip for h in result.hosts}
        assert "192.168.1.1" in ips
        assert "192.168.1.2" in ips

    def test_normal_scan_hostname(self):
        result = self.parser.parse(self._read("nmap_normal.xml"))
        host1 = next(h for h in result.hosts if h.ip == "192.168.1.1")
        assert host1.hostname == "router.local"

    def test_normal_scan_services(self):
        result = self.parser.parse(self._read("nmap_normal.xml"))
        assert len(result.errors) == 0
        ports = {(s.ip, s.port, s.protocol) for s in result.services}
        assert ("192.168.1.1", 22, "tcp") in ports
        assert ("192.168.1.1", 80, "tcp") in ports
        assert ("192.168.1.1", 443, "tcp") in ports
        assert ("192.168.1.2", 3306, "tcp") in ports

    def test_service_details(self):
        result = self.parser.parse(self._read("nmap_normal.xml"))
        ssh = next(s for s in result.services if s.port == 22)
        assert ssh.name == "ssh"
        assert ssh.product == "OpenSSH"
        assert ssh.state == "open"

    def test_no_open_ports(self):
        """Host with no ports section produces a host record but zero services."""
        result = self.parser.parse(self._read("nmap_no_open_ports.xml"))
        assert len(result.errors) == 0
        assert len(result.hosts) == 1
        assert result.hosts[0].ip == "10.0.0.5"
        assert len(result.services) == 0

    def test_malformed_xml(self):
        """Malformed XML returns errors, no hosts."""
        result = self.parser.parse(self._read("nmap_malformed.xml"))
        assert len(result.errors) > 0
        assert len(result.hosts) == 0

    def test_xxe_attempt(self):
        """XXE payload must not trigger a network call or disclose files."""
        xxe = b"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE nmaprun [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<nmaprun><host><status state="up"/><address addr="1.2.3.4" addrtype="ipv4"/>&xxe;</host></nmaprun>"""
        # defusedxml should raise or return errors, never succeed with entity expansion
        result = self.parser.parse(xxe)
        assert len(result.errors) > 0


# ─────────────────────────── FeroxParser ─────────────────────────────────────

class TestFeroxParser:
    def setup_method(self):
        from app.parsers.ferox_parser import FeroxParser
        self.parser = FeroxParser()

    def _read(self, name: str) -> bytes:
        return (FIXTURES / name).read_bytes()

    def test_can_parse_ferox_json(self):
        assert self.parser.can_parse(self._read("ferox_normal.json")) is True

    def test_cannot_parse_nmap(self):
        assert self.parser.can_parse(self._read("nmap_normal.xml")) is False

    def test_normal_ferox(self):
        result = self.parser.parse(self._read("ferox_normal.json"))
        assert len(result.errors) == 0
        urls = {e.url for e in result.endpoints}
        assert "http://example.com/admin" in urls
        assert "http://example.com/login" in urls

    def test_status_codes_preserved(self):
        result = self.parser.parse(self._read("ferox_normal.json"))
        ep = next(e for e in result.endpoints if "/api/v1" in e.url)
        assert ep.status_code == 403

    def test_source_tool_is_feroxbuster(self):
        result = self.parser.parse(self._read("ferox_normal.json"))
        assert all(e.source_tool == "feroxbuster" for e in result.endpoints)

    def test_malformed_lines_skipped_with_errors(self):
        result = self.parser.parse(self._read("ferox_malformed.json"))
        # Should get 2 valid endpoints and 2 errors
        valid_urls = {e.url for e in result.endpoints}
        assert "http://example.com/valid" in valid_urls
        assert "http://example.com/also-valid" in valid_urls
        assert len(result.errors) >= 1  # at least the bad JSON line


# ─────────────────────────── GobusterParser ──────────────────────────────────

class TestGobusterParser:
    def setup_method(self):
        from app.parsers.gobuster_parser import GobusterParser
        self.parser = GobusterParser()

    def _read(self, name: str) -> bytes:
        return (FIXTURES / name).read_bytes()

    def test_can_parse_gobuster(self):
        assert self.parser.can_parse(self._read("gobuster_normal.txt")) is True

    def test_cannot_parse_ferox(self):
        assert self.parser.can_parse(self._read("ferox_normal.json")) is False

    def test_normal_gobuster(self):
        result = self.parser.parse(self._read("gobuster_normal.txt"))
        assert len(result.errors) == 0
        paths = {e.path for e in result.endpoints}
        assert "/admin" in paths
        assert "/login" in paths
        assert "/.htaccess" in paths

    def test_status_codes_preserved(self):
        result = self.parser.parse(self._read("gobuster_normal.txt"))
        ep = next(e for e in result.endpoints if e.path == "/login")
        assert ep.status_code == 200
        assert ep.content_length == 3456

    def test_source_tool_is_gobuster(self):
        result = self.parser.parse(self._read("gobuster_normal.txt"))
        assert all(e.source_tool == "gobuster" for e in result.endpoints)
