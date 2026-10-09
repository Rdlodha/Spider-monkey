import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, func
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

class Target(Base):
    __tablename__ = "target"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    value: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    
    project: Mapped["Project"] = relationship("Project", back_populates="targets")

class AuditLog(Base):
    __tablename__ = "audit_log"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ts: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    actor: Mapped[str] = mapped_column(String(50), default="local", server_default="local", nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target: Mapped[str] = mapped_column(String(500), nullable=True)
    tool: Mapped[str] = mapped_column(String(100), nullable=True)
    result: Mapped[str] = mapped_column(String(100), nullable=True)
