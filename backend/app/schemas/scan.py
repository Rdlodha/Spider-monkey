"""Pydantic schemas for Scan, Host, Service, and Endpoint API responses."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


# ── Service ──────────────────────────────────────────────────────────────────

class ServiceResponse(BaseModel):
    id: str
    host_id: str
    protocol: str
    port: int
    state: str
    name: Optional[str] = None
    product: Optional[str] = None
    version: Optional[str] = None
    first_seen: datetime
    last_seen: datetime
    scan_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ── Host ──────────────────────────────────────────────────────────────────────

class HostSummary(BaseModel):
    id: str
    project_id: str
    ip: str
    hostname: Optional[str] = None
    first_seen: datetime
    last_seen: datetime
    scan_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class HostDetail(HostSummary):
    services: list[ServiceResponse] = []


# ── Endpoint ─────────────────────────────────────────────────────────────────

class EndpointResponse(BaseModel):
    id: str
    project_id: str
    url: str
    path: Optional[str] = None
    status_code: Optional[int] = None
    content_length: Optional[int] = None
    source_tool: Optional[str] = None
    is_interesting: bool = False
    first_seen: datetime
    last_seen: datetime
    scan_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ── Scan ──────────────────────────────────────────────────────────────────────

class ScanSummary(BaseModel):
    id: str
    project_id: str
    target_id: Optional[str] = None
    tool: str
    scan_type: Optional[str] = None
    status: str
    raw_path: Optional[str] = None
    raw_sha256: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScanDetail(ScanSummary):
    hosts: list[HostSummary] = []
    endpoints: list[EndpointResponse] = []
