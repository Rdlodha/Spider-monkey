"""
Deterministic correlation engine.

Rules are static tables in code. Each rule checks Host/Service/Endpoint
data and produces a CorrelationSuggestion. The user accepts or dismisses;
nothing is auto-created as truth.
"""
from dataclasses import dataclass
from typing import Callable
from sqlalchemy.orm import Session

from app.models.base import Host, Service, Endpoint
from app.schemas.findings import CorrelationSuggestion


@dataclass
class Rule:
    rule_id: str
    severity: str
    title: str
    description: str


# ── Port / Service rules ──────────────────────────────────────────────────────

_SERVICE_RULES: list[tuple[set[int], str, Rule]] = [
    (
        {3306},
        "mysql",
        Rule(
            rule_id="SVC-001",
            severity="MEDIUM",
            title="MySQL service exposed",
            description="Port 3306 (MySQL) is open. Verify it is not reachable from untrusted networks and uses strong credentials.",
        ),
    ),
    (
        {5432},
        "postgresql",
        Rule(
            rule_id="SVC-002",
            severity="MEDIUM",
            title="PostgreSQL service exposed",
            description="Port 5432 (PostgreSQL) is open. Ensure it is firewalled and access-controlled.",
        ),
    ),
    (
        {1433},
        "ms-sql-s",
        Rule(
            rule_id="SVC-003",
            severity="MEDIUM",
            title="MSSQL service exposed",
            description="Port 1433 (Microsoft SQL Server) is open. Verify authentication and network access controls.",
        ),
    ),
    (
        {27017, 27018},
        "mongod",
        Rule(
            rule_id="SVC-004",
            severity="HIGH",
            title="MongoDB service exposed",
            description="A MongoDB port is open. Unauthenticated MongoDB instances have been widely exploited.",
        ),
    ),
    (
        {6379},
        "redis",
        Rule(
            rule_id="SVC-005",
            severity="HIGH",
            title="Redis service exposed",
            description="Port 6379 (Redis) is open. Redis has no authentication by default; confirm requirepass is set.",
        ),
    ),
    (
        {21},
        "ftp",
        Rule(
            rule_id="SVC-006",
            severity="MEDIUM",
            title="FTP service exposed",
            description="Port 21 (FTP) is open. FTP transmits credentials in cleartext. Consider disabling or replacing with SFTP.",
        ),
    ),
    (
        {23},
        "telnet",
        Rule(
            rule_id="SVC-007",
            severity="HIGH",
            title="Telnet service exposed",
            description="Port 23 (Telnet) is open. Telnet is unencrypted. Replace with SSH.",
        ),
    ),
    (
        {445},
        "microsoft-ds",
        Rule(
            rule_id="SVC-008",
            severity="HIGH",
            title="SMB service exposed",
            description="Port 445 (SMB) is open. Check for EternalBlue / PrintNightmare exposure and ensure patching.",
        ),
    ),
    (
        {5900, 5901},
        "vnc",
        Rule(
            rule_id="SVC-009",
            severity="HIGH",
            title="VNC remote access exposed",
            description="A VNC port is open. Remote desktop without strong authentication is a critical risk.",
        ),
    ),
    (
        {3389},
        "ms-wbt-server",
        Rule(
            rule_id="SVC-010",
            severity="MEDIUM",
            title="RDP remote access exposed",
            description="Port 3389 (RDP) is open. Verify NLA is enforced and the service is not externally reachable.",
        ),
    ),
    (
        {8080, 8443, 8888, 9090, 9200, 9300},
        "",
        Rule(
            rule_id="SVC-011",
            severity="INFO",
            title="Non-standard web / service port open",
            description="A non-standard port commonly associated with admin panels, proxies, or databases is open. Investigate.",
        ),
    ),
]


# ── Endpoint rules ────────────────────────────────────────────────────────────

_INTERESTING_PATHS = {
    "/admin", "/administrator", "/wp-admin", "/phpmyadmin",
    "/manager", "/console", "/actuator", "/metrics", "/health",
    "/.env", "/.git", "/backup", "/config", "/api/docs",
    "/swagger", "/swagger-ui", "/graphql", "/debug",
}


def _endpoint_label(ep: Endpoint) -> str:
    return ep.url or ep.path or ep.id


def _service_label(svc: Service, host: Host) -> str:
    parts = [host.ip, f":{svc.port}/{svc.protocol}"]
    if svc.name:
        parts.append(f" {svc.name}")
    if svc.product:
        parts.append(f" ({svc.product})")
    return "".join(parts)


# ── Public API ────────────────────────────────────────────────────────────────

def run_correlation(db: Session, project_id: str) -> list[CorrelationSuggestion]:
    suggestions: list[CorrelationSuggestion] = []

    # Load all services for the project (via host)
    hosts = db.query(Host).filter(Host.project_id == project_id).all()
    host_map = {h.id: h for h in hosts}

    for host in hosts:
        for svc in host.services:
            if svc.state != "open":
                continue
            for ports, svc_name_hint, rule in _SERVICE_RULES:
                if svc.port in ports:
                    suggestions.append(
                        CorrelationSuggestion(
                            rule_id=rule.rule_id,
                            severity=rule.severity,
                            title=rule.title,
                            description=rule.description,
                            entity_type="service",
                            entity_id=svc.id,
                            entity_label=_service_label(svc, host),
                        )
                    )

    # Endpoint path analysis
    endpoints = (
        db.query(Endpoint)
        .filter(Endpoint.project_id == project_id)
        .all()
    )
    for ep in endpoints:
        path_lower = (ep.path or "").lower().rstrip("/")
        if path_lower in _INTERESTING_PATHS:
            suggestions.append(
                CorrelationSuggestion(
                    rule_id="EP-001",
                    severity="INFO",
                    title=f"Interesting path discovered: {ep.path}",
                    description=(
                        f"The path '{ep.path}' is commonly associated with admin interfaces, "
                        "configuration exposure, or sensitive data. Review manually."
                    ),
                    entity_type="endpoint",
                    entity_id=ep.id,
                    entity_label=_endpoint_label(ep),
                )
            )
        if ep.status_code == 200 and ep.path and ep.path.lower() in ("/.env", "/.git/HEAD", "/config"):
            suggestions.append(
                CorrelationSuggestion(
                    rule_id="EP-002",
                    severity="HIGH",
                    title=f"Sensitive file accessible: {ep.path}",
                    description=(
                        f"'{ep.path}' returned HTTP 200. This may expose credentials or source code."
                    ),
                    entity_type="endpoint",
                    entity_id=ep.id,
                    entity_label=_endpoint_label(ep),
                )
            )

    # Deduplicate by (rule_id, entity_id)
    seen: set[tuple[str, str]] = set()
    unique: list[CorrelationSuggestion] = []
    for s in suggestions:
        key = (s.rule_id, s.entity_id)
        if key not in seen:
            seen.add(key)
            unique.append(s)

    return unique
