"""
0003_findings_checklists.py
Migration: Finding, FindingLink, Evidence, ChecklistTemplate,
           ChecklistTemplateItem, ChecklistProgress
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Finding ───────────────────────────────────────────────────────────────
    op.create_table(
        "finding",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36),
                  sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "severity",
            sa.String(20),
            nullable=False,
            server_default="INFO",
        ),  # INFO|LOW|MEDIUM|HIGH|CRITICAL
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="OPEN",
        ),  # OPEN|INVESTIGATING|CONFIRMED|FALSE_POSITIVE|RESOLVED
        sa.Column("source_tool", sa.String(50), nullable=True),
        sa.Column("source_scan_id", sa.String(36),
                  sa.ForeignKey("scan.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("tags", sa.String(500), nullable=True),  # comma-separated
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # ── FindingLink ───────────────────────────────────────────────────────────
    op.create_table(
        "finding_link",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("finding_id", sa.String(36),
                  sa.ForeignKey("finding.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_type", sa.String(20), nullable=False),  # host|service|endpoint
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.UniqueConstraint("finding_id", "entity_type", "entity_id",
                            name="uq_finding_link"),
    )

    # ── Evidence ──────────────────────────────────────────────────────────────
    op.create_table(
        "evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("finding_id", sa.String(36),
                  sa.ForeignKey("finding.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        # screenshot|request_response|tool_output|note
        sa.Column("path", sa.String(500), nullable=True),   # file on disk
        sa.Column("text", sa.Text, nullable=True),          # pasted text / note body
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("size", sa.Integer, nullable=True),
        sa.Column("original_filename", sa.String(255), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # ── ChecklistTemplate ─────────────────────────────────────────────────────
    op.create_table(
        "checklist_template",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # ── ChecklistTemplateItem ─────────────────────────────────────────────────
    op.create_table(
        "checklist_template_item",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("template_id", sa.String(36),
                  sa.ForeignKey("checklist_template.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section", sa.String(100), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
    )

    # ── ChecklistProgress ─────────────────────────────────────────────────────
    op.create_table(
        "checklist_progress",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("target_id", sa.String(36),
                  sa.ForeignKey("target.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_item_id", sa.String(36),
                  sa.ForeignKey("checklist_template_item.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column(
            "state",
            sa.String(20),
            nullable=False,
            server_default="NOT_STARTED",
        ),  # NOT_STARTED|IN_PROGRESS|COMPLETED|NOT_APPLICABLE
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("target_id", "template_item_id",
                            name="uq_progress_target_item"),
    )

    # ── is_interesting flags on host and service ──────────────────────────────
    op.add_column(
        "host",
        sa.Column("is_interesting", sa.Boolean, server_default="false", nullable=False),
    )
    op.add_column(
        "service",
        sa.Column("is_interesting", sa.Boolean, server_default="false", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("service", "is_interesting")
    op.drop_column("host", "is_interesting")
    op.drop_table("checklist_progress")
    op.drop_table("checklist_template_item")
    op.drop_table("checklist_template")
    op.drop_table("evidence")
    op.drop_table("finding_link")
    op.drop_table("finding")
