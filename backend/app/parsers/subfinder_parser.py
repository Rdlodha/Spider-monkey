"""
Subfinder JSON output parser.

Subfinder is run with the -oJ flag which produces one JSON object per line:
  {"host":"api.example.com","input":"example.com","source":"crtsh","ip":"1.2.3.4","type":"subdomain"}

Each record becomes a ParsedHost (hostname = subdomain, ip = ip if present).
Records without a host field are skipped with an error note.
"""
import json
from app.parsers import BaseParser, ParseResult, ParsedHost


class SubfinderParser(BaseParser):
    name = "subfinder"

    def can_parse(self, content: bytes) -> bool:
        """Detect Subfinder JSON-lines: first valid JSON line must have a 'host' key
        and optionally a 'source' or 'input' key (subfinder-specific fields)."""
        for line in content.split(b"\n"):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                # Must have 'host' AND at least one subfinder-specific key
                return "host" in obj and ("source" in obj or "input" in obj)
            except Exception:
                return False
        return False

    def parse(self, content: bytes) -> ParseResult:
        result = ParseResult()
        lines = content.decode("utf-8", errors="replace").splitlines()

        seen: set[str] = set()  # deduplicate hostnames

        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue

            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                result.errors.append(f"Line {i}: JSON decode error — {e}")
                continue

            host = obj.get("host") or obj.get("subdomain")
            if not host:
                result.errors.append(f"Line {i}: missing 'host' field — skipped")
                continue

            host = host.strip().lower()
            if host in seen:
                continue
            seen.add(host)

            # IP is optional — subfinder may not always resolve
            ip = obj.get("ip") or obj.get("ip_address")
            if ip:
                ip = ip.strip()

            # Store as a host: use the IP as ip if present, else use hostname as a
            # placeholder IP so the import service can still create a Host record.
            # The hostname field carries the actual subdomain name.
            result.hosts.append(ParsedHost(
                ip=ip if ip else host,   # fallback: hostname as ip placeholder
                hostname=host,
            ))

        return result
