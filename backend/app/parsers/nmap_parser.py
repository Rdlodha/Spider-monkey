"""
Nmap XML parser using defusedxml (safe against XXE attacks).
Only parses Nmap XML output (not human-readable text format).
"""
import defusedxml.ElementTree as ET
from app.parsers import BaseParser, ParseResult, ParsedHost, ParsedService


class NmapParser(BaseParser):
    name = "nmap"

    def can_parse(self, content: bytes) -> bool:
        """Detect Nmap XML by checking for the nmaprun root element."""
        # Quick sniff — look for the nmaprun opening tag in the first 512 bytes
        head = content[:512]
        return b"<nmaprun" in head

    def parse(self, content: bytes) -> ParseResult:
        result = ParseResult()

        try:
            root = ET.fromstring(content)
        except Exception as e:
            result.errors.append(f"XML parse error: {e}")
            return result

        if root.tag != "nmaprun":
            result.errors.append(f"Not an nmaprun document; root tag is '{root.tag}'")
            return result

        for host_elem in root.findall("host"):
            # --- Status ---
            status_elem = host_elem.find("status")
            if status_elem is None:
                continue
            host_status = status_elem.get("state", "unknown")

            # --- IP + hostname ---
            ip = None
            hostname = None

            for addr in host_elem.findall("address"):
                addrtype = addr.get("addrtype", "")
                if addrtype in ("ipv4", "ipv6"):
                    ip = addr.get("addr")

            hostnames_elem = host_elem.find("hostnames")
            if hostnames_elem is not None:
                hn = hostnames_elem.find("hostname")
                if hn is not None:
                    hostname = hn.get("name")

            if not ip:
                result.errors.append("Host entry missing IP address — skipped")
                continue

            result.hosts.append(ParsedHost(ip=ip, hostname=hostname))

            # --- Ports / services ---
            ports_elem = host_elem.find("ports")
            if ports_elem is None:
                continue

            for port_elem in ports_elem.findall("port"):
                protocol = port_elem.get("protocol", "tcp")
                try:
                    portid = int(port_elem.get("portid", "0"))
                except ValueError:
                    result.errors.append(f"Invalid port number for host {ip} — skipped")
                    continue

                state_elem = port_elem.find("state")
                state = state_elem.get("state", "unknown") if state_elem is not None else "unknown"

                svc_elem = port_elem.find("service")
                svc_name = svc_product = svc_version = None
                if svc_elem is not None:
                    svc_name = svc_elem.get("name")
                    svc_product = svc_elem.get("product")
                    svc_version = svc_elem.get("version")

                result.services.append(ParsedService(
                    ip=ip,
                    protocol=protocol,
                    port=portid,
                    state=state,
                    name=svc_name or None,
                    product=svc_product or None,
                    version=svc_version or None,
                ))

        return result
