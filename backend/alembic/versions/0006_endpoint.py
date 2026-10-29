"""Add endpoint table

Revision ID: 0006_endpoint
Revises: 0005_proxy_profile
Create Date: 2026-10-13
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_endpoint"
down_revision = "0005_proxy_profile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "endpoint",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False),
        sa.Column("host_id", sa.String(36), sa.ForeignKey("host.id", ondelete="SET NULL"), nullable=True),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("path", sa.String(2048), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("content_length", sa.Integer(), nullable=True),
        sa.Column("source_tool", sa.String(50), nullable=True),
        sa.Column("is_interesting", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("first_seen", sa.DateTime(), nullable=False),
        sa.Column("last_seen", sa.DateTime(), nullable=False),
        sa.Column("scan_id", sa.String(36), sa.ForeignKey("scan.id", ondelete="SET NULL"), nullable=True),
        sa.UniqueConstraint("project_id", "url", name="uq_endpoint_project_url"),
    )


def downgrade() -> None:
    op.drop_table("endpoint")
