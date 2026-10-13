import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Integer, Text, Boolean, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "project"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    authorized_ack_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    targets: Mapped[list["Target"]] = relationship("Target", back_populates="project", cascade="all, delete-orphan")
    findings: Mapped[list["Finding"]] = relationship("Finding", back_populates="project", cascade="all, delete-orphan")


class Target(Base):
    __tablename__ = "target"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    value: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    project: Mapped["Project"] = relationship("Project", back_populates="targets")
    checklist_progress: Mapped[list["ChecklistProgress"]] = relationship(
        "ChecklistProgress", back_populates="target", cascade="all, delete-orphan"
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ts: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    actor: Mapped[str] = mapped_column(String(50), default="local", server_default="local", nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target: Mapped[str] = mapped_column(String(500), nullable=True)
    tool: Mapped[str] = mapped_column(String(100), nullable=True)
    result: Mapped[str] = mapped_column(String(100), nullable=True)


class Scan(Base):
    __tablename__ = "scan"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("target.id", ondelete="SET NULL"), nullable=True)
    tool: Mapped[str] = mapped_column(String(50), nullable=False)
    scan_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued", server_default="queued")
    raw_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    hosts: Mapped[list["Host"]] = relationship("Host", back_populates="scan", foreign_keys="Host.scan_id")
    endpoints: Mapped[list["Endpoint"]] = relationship("Endpoint", back_populates="scan", foreign_keys="Endpoint.scan_id")


class Host(Base):
    __tablename__ = "host"
    __table_args__ = (UniqueConstraint("project_id", "ip", name="uq_host_project_ip"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    ip: Mapped[str] = mapped_column(String(45), nullable=False)
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    scan_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("scan.id", ondelete="SET NULL"), nullable=True)
    is_interesting: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    scan: Mapped["Scan | None"] = relationship("Scan", back_populates="hosts", foreign_keys=[scan_id])
    services: Mapped[list["Service"]] = relationship("Service", back_populates="host", cascade="all, delete-orphan")


class Service(Base):
    __tablename__ = "service"
    __table_args__ = (UniqueConstraint("host_id", "protocol", "port", name="uq_service_host_proto_port"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    host_id: Mapped[str] = mapped_column(String(36), ForeignKey("host.id", ondelete="CASCADE"), nullable=False)
    protocol: Mapped[str] = mapped_column(String(10), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    product: Mapped[str | None] = mapped_column(String(200), nullable=True)
    version: Mapped[str | None] = mapped_column(String(200), nullable=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    scan_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("scan.id", ondelete="SET NULL"), nullable=True)
    is_interesting: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    host: Mapped["Host"] = relationship("Host", back_populates="services")


class Endpoint(Base):
    __tablename__ = "endpoint"
    __table_args__ = (UniqueConstraint("project_id", "url", name="uq_endpoint_project_url"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    host_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("host.id", ondelete="SET NULL"), nullable=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_length: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_tool: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_interesting: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    first_seen: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    scan_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("scan.id", ondelete="SET NULL"), nullable=True)

    scan: Mapped["Scan | None"] = relationship("Scan", back_populates="endpoints", foreign_keys=[scan_id])


# ── M3 Models ──────────────────────────────────────────────────────────────────

class Finding(Base):
    __tablename__ = "finding"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # INFO | LOW | MEDIUM | HIGH | CRITICAL
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="INFO", server_default="INFO")
    # OPEN | INVESTIGATING | CONFIRMED | FALSE_POSITIVE | RESOLVED
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN", server_default="OPEN")
    source_tool: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_scan_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("scan.id", ondelete="SET NULL"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[str | None] = mapped_column(String(500), nullable=True)  # comma-separated
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    project: Mapped["Project"] = relationship("Project", back_populates="findings")
    links: Mapped[list["FindingLink"]] = relationship("FindingLink", back_populates="finding", cascade="all, delete-orphan")
    evidence: Mapped[list["Evidence"]] = relationship("Evidence", back_populates="finding", cascade="all, delete-orphan")


class FindingLink(Base):
    __tablename__ = "finding_link"
    __table_args__ = (UniqueConstraint("finding_id", "entity_type", "entity_id", name="uq_finding_link"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    finding_id: Mapped[str] = mapped_column(String(36), ForeignKey("finding.id", ondelete="CASCADE"), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)  # host | service | endpoint
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)

    finding: Mapped["Finding"] = relationship("Finding", back_populates="links")


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    finding_id: Mapped[str] = mapped_column(String(36), ForeignKey("finding.id", ondelete="CASCADE"), nullable=False)
    # screenshot | request_response | tool_output | note
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    finding: Mapped["Finding"] = relationship("Finding", back_populates="evidence")


class ChecklistTemplate(Base):
    __tablename__ = "checklist_template"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    items: Mapped[list["ChecklistTemplateItem"]] = relationship(
        "ChecklistTemplateItem", back_populates="template", cascade="all, delete-orphan",
        order_by="ChecklistTemplateItem.sort_order"
    )


class ChecklistTemplateItem(Base):
    __tablename__ = "checklist_template_item"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    template_id: Mapped[str] = mapped_column(String(36), ForeignKey("checklist_template.id", ondelete="CASCADE"), nullable=False)
    section: Mapped[str | None] = mapped_column(String(100), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    template: Mapped["ChecklistTemplate"] = relationship("ChecklistTemplate", back_populates="items")


class ChecklistProgress(Base):
    __tablename__ = "checklist_progress"
    __table_args__ = (UniqueConstraint("target_id", "template_item_id", name="uq_progress_target_item"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    target_id: Mapped[str] = mapped_column(String(36), ForeignKey("target.id", ondelete="CASCADE"), nullable=False)
    template_item_id: Mapped[str] = mapped_column(String(36), ForeignKey("checklist_template_item.id", ondelete="CASCADE"), nullable=False)
    # NOT_STARTED | IN_PROGRESS | COMPLETED | NOT_APPLICABLE
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="NOT_STARTED", server_default="NOT_STARTED")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    target: Mapped["Target"] = relationship("Target", back_populates="checklist_progress")
    template_item: Mapped["ChecklistTemplateItem"] = relationship("ChecklistTemplateItem")
