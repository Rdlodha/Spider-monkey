"""
Feroxbuster JSON-lines parser.
Each line is a JSON object with at least: url, status, content_length.
Lines that cannot be parsed are recorded as errors and skipped.
"""
import json
from urllib.parse import urlparse, urlunparse
from app.parsers import BaseParser, ParseResult, ParsedEndpoint


def _normalize_url(raw: str) -> str:
    """Lowercase scheme+host, strip default ports, strip fragment."""
    try:
        parsed = urlparse(raw)
        scheme = parsed.scheme.lower()
        host = parsed.hostname or ""
        port = parsed.port
        # Strip default ports
        if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
            netloc = host
        elif port:
            netloc = f"{host}:{port}"
        else:
            netloc = host
        return urlunparse((scheme, netloc, parsed.path, parsed.params, parsed.query, ""))
    except Exception:
        return raw


class FeroxParser(BaseParser):
    name = "feroxbuster"

    def can_parse(self, content: bytes) -> bool:
        """Detect Feroxbuster JSON-lines: first non-empty line should be valid JSON with a 'url' key."""
        for line in content.split(b"\n"):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                return "url" in obj
            except Exception:
                return False
        return False

    def parse(self, content: bytes) -> ParseResult:
        result = ParseResult()
        lines = content.decode("utf-8", errors="replace").splitlines()
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                result.errors.append(f"Line {i}: JSON decode error — {e}")
                continue

            url = obj.get("url")
            if not url:
                result.errors.append(f"Line {i}: missing 'url' field — skipped")
                continue

            normalized = _normalize_url(url)
            path = urlparse(normalized).path or None

            result.endpoints.append(ParsedEndpoint(
                url=normalized,
                path=path,
                status_code=obj.get("status"),
                content_length=obj.get("content_length"),
                source_tool="feroxbuster",
            ))
        return result
