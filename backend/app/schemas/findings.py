"""Pydantic schemas for M3: Finding, Evidence, Checklist, Correlation, Dashboard."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


# ── Finding ───────────────────────────────────────────────────────────────────

class FindingLinkSchema(BaseModel):
    entity_type: str   # host | service | endpoint
    entity_id: str

    model_config = ConfigDict(from_attributes=True)


class FindingCreate(BaseModel):
    project_id: str
    title: str
    description: Optional[str] = None
    severity: str = "INFO"
    status: str = "OPEN"
    source_tool: Optional[str] = None
    source_scan_id: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[str] = None
    links: list[FindingLinkSchema] = []


class FindingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[str] = None


class FindingLinkResponse(BaseModel):
    id: str
    entity_type: str
    entity_id: str

    model_config = ConfigDict(from_attributes=True)


class EvidenceResponse(BaseModel):
    id: str
    finding_id: str
    kind: str
    path: Optional[str] = None
    text: Optional[str] = None
    sha256: Optional[str] = None
    size: Optional[int] = None
    original_filename: Optional[str] = None
    mime_type: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FindingSummary(BaseModel):
    id: str
    project_id: str
    title: str
    severity: str
    status: str
    source_tool: Optional[str] = None
    tags: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FindingDetail(FindingSummary):
    description: Optional[str] = None
    source_scan_id: Optional[str] = None
    notes: Optional[str] = None
    links: list[FindingLinkResponse] = []
    evidence: list[EvidenceResponse] = []


# ── Checklist ─────────────────────────────────────────────────────────────────

class ChecklistTemplateItemResponse(BaseModel):
    id: str
    template_id: str
    section: Optional[str] = None
    title: str
    description: Optional[str] = None
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


class ChecklistTemplateResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    items: list[ChecklistTemplateItemResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ChecklistProgressUpdate(BaseModel):
    state: str   # NOT_STARTED|IN_PROGRESS|COMPLETED|NOT_APPLICABLE
    note: Optional[str] = None


class ChecklistProgressResponse(BaseModel):
    id: str
    target_id: str
    template_item_id: str
    state: str
    note: Optional[str] = None
    updated_at: datetime

    # Inline the item details for convenient frontend rendering
    item_section: Optional[str] = None
    item_title: str = ""
    item_sort_order: int = 0

    model_config = ConfigDict(from_attributes=True)


# ── Correlation ────────────────────────────────────────────────────────────────

class CorrelationSuggestion(BaseModel):
    rule_id: str
    severity: str
    title: str
    description: str
    entity_type: str   # host | service | endpoint
    entity_id: str
    entity_label: str  # human-readable (e.g., "192.168.1.1:3306/tcp mysql")


class CorrelationResult(BaseModel):
    project_id: str
    suggestions: list[CorrelationSuggestion]


# ── Dashboard ─────────────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    project_id: str
    host_count: int
    open_port_count: int
    endpoint_count: int
    finding_count: int
    critical_finding_count: int
    high_finding_count: int
    checklist_completed: int
    checklist_total: int
