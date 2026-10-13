"""Add ProxyProfile table and proxy_profile_id to Job

Revision ID: 0005_proxy_profile
Revises: 0004_scope_and_jobs
Create Date: 2026-10-13
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_proxy_profile"
down_revision = "0004_scope_and_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "proxy_profile",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("type", sa.String(20), nullable=False, server_default="DIRECT"),
        sa.Column("host", sa.String(255), nullable=True),
        sa.Column("port", sa.Integer(), nullable=True),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("encrypted_password", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    # SQLite does not support adding a FK constraint via ALTER TABLE.
    # We add the column without the FK definition; the application-level relationship
    # still works because SQLAlchemy resolves it at query time.
    op.add_column(
        "job",
        sa.Column("proxy_profile_id", sa.String(36), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("job", "proxy_profile_id")
    op.drop_table("proxy_profile")
