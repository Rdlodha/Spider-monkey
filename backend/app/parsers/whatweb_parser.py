"""
WhatWeb JSON output parser.

WhatWeb is run with: whatweb -a 3 --log-json=output.json http://target
Each line in the log is a JSON object:
  {
    "target": "http://example.com",
    "http_status": 200,
    "plugins": {
      "Apache": {"string": ["2.4.51"], "version": ["2.4.51"]},
      "PHP": {"string": ["7.4.3"]},
      "Bootstrap": {},
      "Title": {"string": ["Welcome to Example"]}
    }
  }

Each record becomes:
- A ParsedHost (from target URL hostname)
- A ParsedService (HTTP port from URL)
- A ParsedEndpoint (the target URL itself)

Technology fingerprints from 'plugins' are encoded into source_tool for
display in the UI and future finding automation.
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


# Known server products to extract from WhatWeb plugins for service records
_SERVER_PLUGINS = {"Apache", "Nginx", "IIS", "LiteSpeed", "Lighttpd", "Caddy", "Tomcat", "Jetty"}
_SKIP_TECH = {"Title", "Country", "IP", "HTTPServer", "Cookies", "HTML5", "Meta-Author",
              "Meta-Refresh", "Open-Graph-Protocol", "Strict-Transport-Security",
              "X-Frame-Options", "X-XSS-Protection", "X-Content-Type-Options"}


class WhatWebParser(BaseParser):
    name = "whatweb"

    def can_parse(self, content: bytes) -> bool:
        """Detect WhatWeb JSON log: first valid JSON line must have 'target' + 'plugins' keys."""
        for line in content.split(b"\n"):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                return "target" in obj and "plugins" in obj
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

            target = obj.get("target")
            if not target:
                result.errors.append(f"Line {i}: missing 'target' field — skipped")
                continue

            normalized = _normalize_url(target)
            parsed_url = urlparse(normalized)
            hostname = parsed_url.hostname or ""
            status_code = obj.get("http_status")
            plugins: dict = obj.get("plugins") or {}

            # --- Host ---
            if hostname and hostname not in seen_hosts:
                seen_hosts.add(hostname)
                result.hosts.append(ParsedHost(ip=hostname, hostname=hostname))

            # --- Service: try to find a server-type plugin ---
            port = parsed_url.port or (443 if parsed_url.scheme == "https" else 80)
            svc_name = "https" if parsed_url.scheme == "https" else "http"
            svc_product = None
            svc_version = None

            for plugin_name in _SERVER_PLUGINS:
                if plugin_name in plugins:
                    plugin_data = plugins[plugin_name]
                    svc_product = plugin_name
                    versions = (plugin_data.get("version") or plugin_data.get("string") or [])
                    if versions:
                        svc_version = versions[0]
                    break

            if hostname:
                result.services.append(ParsedService(
                    ip=hostname,
                    protocol="tcp",
                    port=port,
                    state="open",
                    name=svc_name,
                    product=svc_product,
                    version=svc_version,
                ))

            # --- Endpoint ---
            # Build tech fingerprint string from all plugins (skip noisy ones)
            tech_parts = []
            for plugin_name, plugin_data in plugins.items():
                if plugin_name in _SKIP_TECH:
                    continue
                if isinstance(plugin_data, dict):
                    versions = plugin_data.get("version") or plugin_data.get("string") or []
                    if versions:
                        tech_parts.append(f"{plugin_name}/{versions[0]}")
                    else:
                        tech_parts.append(plugin_name)

            tech_str = ",".join(tech_parts[:8]) if tech_parts else None  # cap at 8 techs
            source = f"whatweb:{tech_str}" if tech_str else "whatweb"

            result.endpoints.append(ParsedEndpoint(
                url=normalized,
                path=parsed_url.path or "/",
                status_code=status_code,
                content_length=None,
                source_tool=source,
            ))

        return result
