"""
Amass JSON output parser.

Amass is run with: amass enum -d example.com -json output.json
Each line is a JSON object with this structure:
  {
    "name": "api.example.com",
    "domain": "example.com",
    "addresses": [{"ip": "1.2.3.4", "cidr": "1.2.3.0/24", "asn": 12345, "desc": "..."}],
    "tag": "cert",
    "source": "CertSpotter"
  }

Each record becomes a ParsedHost per unique IP/hostname combination.
If multiple IPs exist, we create a host entry per IP.
"""
import json
from app.parsers import BaseParser, ParseResult, ParsedHost


class AmassParser(BaseParser):
    name = "amass"

    def can_parse(self, content: bytes) -> bool:
        """Detect Amass JSON output by looking for 'name' + 'addresses' or 'domain' keys."""
        for line in content.split(b"\n"):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                # Amass-specific: has 'name' and 'addresses' (list) or 'domain'
                return "name" in obj and ("addresses" in obj or "domain" in obj)
            except Exception:
                return False
        return False

    def parse(self, content: bytes) -> ParseResult:
        result = ParseResult()
        lines = content.decode("utf-8", errors="replace").splitlines()

        seen: set[tuple[str, str]] = set()  # (ip, hostname)

        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue

            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                result.errors.append(f"Line {i}: JSON decode error — {e}")
                continue

            hostname = obj.get("name") or obj.get("subdomain")
            if not hostname:
                result.errors.append(f"Line {i}: missing 'name' field — skipped")
                continue

            hostname = hostname.strip().lower()
            addresses = obj.get("addresses", [])

            if addresses:
                # Create one host record per resolved IP
                for addr in addresses:
                    ip = addr.get("ip") if isinstance(addr, dict) else str(addr)
                    if not ip:
                        continue
                    ip = ip.strip()
                    key = (ip, hostname)
                    if key in seen:
                        continue
                    seen.add(key)
                    result.hosts.append(ParsedHost(ip=ip, hostname=hostname))
            else:
                # No IPs resolved — store hostname as placeholder
                key = (hostname, hostname)
                if key not in seen:
                    seen.add(key)
                    result.hosts.append(ParsedHost(ip=hostname, hostname=hostname))

        return result
