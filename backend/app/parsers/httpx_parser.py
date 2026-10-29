"""
Httpx JSON output parser.

Httpx is run with: httpx -l urls.txt -json -o output.json
Each line is a JSON object. Key fields:
  {
    "url": "http://example.com",
    "status-code": 200,
    "content-length": 4321,
    "title": "Example Domain",
    "webserver": "nginx/1.21.3",
    "tech": ["Nginx", "Bootstrap"],
    "host": "1.2.3.4",
    "port": "80",
    "scheme": "http",
    "input": "example.com"
  }

Each record becomes:
- A ParsedHost (if host IP is present)
- A ParsedService (if host + port are present)
- A ParsedEndpoint (always, from the URL)

Technology and webserver info are stored in ParsedEndpoint.source_tool tag
so they appear in the scan and can later be used for fingerprinting findings.
"""
import json
from urllib.parse import urlparse, urlunparse
from app.parsers import BaseParser, ParseResult, ParsedHost, ParsedService, ParsedEndpoint


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


class HttpxParser(BaseParser):
    name = "httpx"

    def can_parse(self, content: bytes) -> bool:
        """Detect httpx JSON-lines: first valid JSON line has 'url' + 'status-code' (httpx-specific)."""
        for line in content.split(b"\n"):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                # httpx uses hyphenated keys like 'status-code' which distinguishes it from feroxbuster
                return "url" in obj and "status-code" in obj
            except Exception:
                return False
        return False

    def parse(self, content: bytes) -> ParseResult:
        result = ParseResult()
        lines = content.decode("utf-8", errors="replace").splitlines()

        seen_hosts: set[str] = set()

        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue

            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                result.errors.append(f"Line {i}: JSON decode error — {e}")
                continue

            url = obj.get("url") or obj.get("input")
            if not url:
                result.errors.append(f"Line {i}: missing 'url' field — skipped")
                continue

            normalized_url = _normalize_url(url)
            parsed_url = urlparse(normalized_url)
            status_code = obj.get("status-code") or obj.get("status_code")
            content_length = obj.get("content-length") or obj.get("content_length")

            # --- Host record ---
            host_ip = obj.get("host")  # httpx resolves and includes the IP
            hostname = parsed_url.hostname or ""

            if host_ip and host_ip not in seen_hosts:
                seen_hosts.add(host_ip)
                result.hosts.append(ParsedHost(
                    ip=host_ip,
                    hostname=hostname if hostname != host_ip else None,
                ))

            # --- Service record ---
            # Detect port: prefer explicit 'port' field, else derive from URL
            port_str = obj.get("port")
            port = int(port_str) if port_str else parsed_url.port
            if not port:
                port = 443 if parsed_url.scheme == "https" else 80

            if host_ip:
                protocol = "tcp"
                # Build service name from webserver or scheme
                webserver = obj.get("webserver") or ""
                svc_name = "https" if parsed_url.scheme == "https" else "http"
                svc_product = webserver.split("/")[0] if webserver else None
                svc_version = webserver.split("/")[1] if webserver and "/" in webserver else None

                result.services.append(ParsedService(
                    ip=host_ip,
                    protocol=protocol,
                    port=port,
                    state="open",
                    name=svc_name,
                    product=svc_product,
                    version=svc_version,
                ))

            # --- Endpoint record ---
            # Encode tech stack info into source_tool tag so it's queryable later
            tech = obj.get("tech") or obj.get("technologies") or []
            tech_str = ",".join(tech) if tech else None
            source = f"httpx:{tech_str}" if tech_str else "httpx"

            result.endpoints.append(ParsedEndpoint(
                url=normalized_url,
                path=parsed_url.path or None,
                status_code=status_code,
                content_length=content_length,
                source_tool=source,
            ))

        return result
