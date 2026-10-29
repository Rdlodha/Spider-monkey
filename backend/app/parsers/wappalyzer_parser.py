"""
Wappalyzer CLI JSON output parser.

The Wappalyzer CLI (wappalyzer / webtech) outputs:
  wappalyzer https://example.com --output=json

Output is a single JSON object (NOT JSON-lines):
  {
    "urls": {
      "https://example.com/": {"status": 200}
    },
    "technologies": [
      {
        "slug": "react",
        "name": "React",
        "confidence": 100,
        "version": "18.2.0",
        "icon": "React.svg",
        "website": "https://reactjs.org",
        "cpe": null,
        "categories": [{"id": 12, "slug": "javascript-frameworks", "name": "JavaScript frameworks"}]
      }
    ]
  }

Alternatively, webtech CLI outputs:
  {
    "https://example.com": ["React", "Bootstrap", "PHP/8.1"]
  }

We support both formats. Each URL becomes:
- A ParsedHost from the hostname in the URL
- A ParsedService (HTTP/HTTPS on appropriate port)
- A ParsedEndpoint with all detected technologies encoded in source_tool
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


def _parse_wappalyzer_format(obj: dict) -> list[tuple[str, int | None, list[str]]]:
    """
    Parse the standard Wappalyzer CLI output format.
    Returns list of (url, status_code, [tech_name_with_version, ...])
    """
    results = []
    urls_dict: dict = obj.get("urls", {})
    technologies: list = obj.get("technologies", [])

    tech_names = []
    for tech in technologies:
        if isinstance(tech, dict):
            name = tech.get("name", "")
            version = tech.get("version") or ""
            if version:
                tech_names.append(f"{name}/{version}")
            else:
                tech_names.append(name)
        elif isinstance(tech, str):
            tech_names.append(tech)

    for url, url_data in urls_dict.items():
        status = url_data.get("status") if isinstance(url_data, dict) else None
        results.append((url, status, tech_names))

    return results


def _parse_webtech_format(obj: dict) -> list[tuple[str, int | None, list[str]]]:
    """
    Parse the webtech CLI output format: {url: [tech1, tech2, ...]}
    Returns list of (url, status_code, [tech_name, ...])
    """
    results = []
    for url, techs in obj.items():
        if isinstance(techs, list):
            tech_names = [str(t) for t in techs]
            results.append((url, None, tech_names))
    return results


class WappalyzerParser(BaseParser):
    name = "wappalyzer"

    def can_parse(self, content: bytes) -> bool:
        """
        Detect Wappalyzer CLI output:
        - Standard format: single JSON object with 'technologies' list and 'urls' dict
        - Webtech format: single JSON object where all values are lists of strings
        """
        content = content.strip()
        if not content.startswith(b"{"):
            return False
        try:
            obj = json.loads(content)
            if not isinstance(obj, dict):
                return False
            # Standard wappalyzer format
            if "technologies" in obj and "urls" in obj:
                return True
            # Webtech format: keys are URLs, values are lists
            if obj:
                first_val = next(iter(obj.values()))
                first_key = next(iter(obj.keys()))
                return isinstance(first_val, list) and (
                    first_key.startswith("http://") or first_key.startswith("https://")
                )
        except Exception:
            return False
        return False

    def parse(self, content: bytes) -> ParseResult:
        result = ParseResult()

        try:
            obj = json.loads(content.decode("utf-8", errors="replace").strip())
        except json.JSONDecodeError as e:
            result.errors.append(f"JSON decode error: {e}")
            return result

        if not isinstance(obj, dict):
            result.errors.append("Expected a JSON object at root level")
            return result

        # Determine format
        if "technologies" in obj and "urls" in obj:
            entries = _parse_wappalyzer_format(obj)
        else:
            entries = _parse_webtech_format(obj)

        seen_hosts: set[str] = set()

        for url, status_code, tech_names in entries:
            if not url:
                continue

            normalized = _normalize_url(url)
            parsed_url = urlparse(normalized)
            hostname = parsed_url.hostname or ""

            if not hostname:
                result.errors.append(f"Could not extract hostname from URL: {url!r} — skipped")
                continue

            # --- Host ---
            if hostname not in seen_hosts:
                seen_hosts.add(hostname)
                result.hosts.append(ParsedHost(ip=hostname, hostname=hostname))

            # --- Service ---
            port = parsed_url.port or (443 if parsed_url.scheme == "https" else 80)
            svc_name = "https" if parsed_url.scheme == "https" else "http"

            # Try to find a server-side tech for product/version
            server_techs = [t for t in tech_names if any(
                s in t.lower() for s in ("nginx", "apache", "iis", "lighttpd", "caddy", "tomcat")
            )]
            svc_product = server_techs[0].split("/")[0] if server_techs else None
            svc_version = server_techs[0].split("/")[1] if server_techs and "/" in server_techs[0] else None

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
            tech_str = ",".join(tech_names[:10]) if tech_names else None
            source = f"wappalyzer:{tech_str}" if tech_str else "wappalyzer"

            result.endpoints.append(ParsedEndpoint(
                url=normalized,
                path=parsed_url.path or "/",
                status_code=status_code,
                content_length=None,
                source_tool=source,
            ))

        return result
