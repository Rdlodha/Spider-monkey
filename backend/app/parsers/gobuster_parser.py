"""
Gobuster simple text parser.
Gobuster dir output format:
  /path                 (Status: 200) [Size: 1234]
  /admin                (Status: 301) [Size: 0] [--> /admin/]

We parse each line to extract path, status_code, and content_length.
Lines that don't match the expected format are recorded as errors and skipped.
"""
import re
from urllib.parse import urlparse, urlunparse
from app.parsers import BaseParser, ParseResult, ParsedEndpoint

# Pattern for gobuster dir output lines
# e.g.: /path (Status: 200) [Size: 1234]
_LINE_PATTERN = re.compile(
    r"^(/[^\s]*)\s+\(Status:\s*(\d+)\)(?:\s+\[Size:\s*(\d+)\])?",
    re.IGNORECASE,
)

# Pattern for gobuster with full URL prefix (--url flag)
_URL_LINE_PATTERN = re.compile(
    r"^(https?://[^\s]+)\s+\(Status:\s*(\d+)\)(?:\s+\[Size:\s*(\d+)\])?",
    re.IGNORECASE,
)


def _normalize_url(raw: str) -> str:
    try:
        parsed = urlparse(raw)
        scheme = parsed.scheme.lower()
        host = parsed.hostname or ""
        port = parsed.port
        if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
            netloc = host
        elif port:
            netloc = f"{host}:{port}"
        else:
            netloc = host
        return urlunparse((scheme, netloc, parsed.path, parsed.params, parsed.query, ""))
    except Exception:
        return raw


class GobusterParser(BaseParser):
    name = "gobuster"

    def can_parse(self, content: bytes) -> bool:
        """Detect Gobuster output: contains 'Gobuster' header or lines matching the dir format."""
        if b"Gobuster" in content[:256] or b"gobuster" in content[:256]:
            return True
        # Try to match at least one path line
        for line in content.split(b"\n")[:20]:
            decoded = line.decode("utf-8", errors="replace").strip()
            if _LINE_PATTERN.match(decoded) or _URL_LINE_PATTERN.match(decoded):
                return True
        return False

    def parse(self, content: bytes) -> ParseResult:
        result = ParseResult()
        lines = content.decode("utf-8", errors="replace").splitlines()
        base_url: str | None = None

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # Capture base URL from gobuster header line: "Url: http://..."
            if stripped.lower().startswith("url:"):
                base_url = stripped.split(":", 1)[1].strip().rstrip("/")
                continue

            # Try full-URL pattern first
            m = _URL_LINE_PATTERN.match(stripped)
            if m:
                url = _normalize_url(m.group(1))
                status = int(m.group(2))
                size = int(m.group(3)) if m.group(3) else None
                result.endpoints.append(ParsedEndpoint(
                    url=url,
                    path=urlparse(url).path or None,
                    status_code=status,
                    content_length=size,
                    source_tool="gobuster",
                ))
                continue

            # Try path-only pattern
            m = _LINE_PATTERN.match(stripped)
            if m:
                path = m.group(1)
                status = int(m.group(2))
                size = int(m.group(3)) if m.group(3) else None
                if base_url:
                    url = _normalize_url(f"{base_url}{path}")
                else:
                    url = path  # no base URL known; store path as URL
                result.endpoints.append(ParsedEndpoint(
                    url=url,
                    path=path,
                    status_code=status,
                    content_length=size,
                    source_tool="gobuster",
                ))
                continue

            # Non-data lines (headers, progress lines) — skip silently
            # unless they look like they should have matched
            if "(Status:" in stripped:
                result.errors.append(f"Line {i}: unrecognized format — {stripped!r}")

        return result
