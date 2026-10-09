"""scan host service

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-09
"""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'scan',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('project.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_id', sa.String(36), sa.ForeignKey('target.id', ondelete='SET NULL'), nullable=True),
        sa.Column('tool', sa.String(50), nullable=False),
        sa.Column('scan_type', sa.String(50), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='queued'),
        sa.Column('raw_path', sa.String(500), nullable=True),
        sa.Column('raw_sha256', sa.String(64), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('exit_code', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        'host',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('project.id', ondelete='CASCADE'), nullable=False),
        sa.Column('ip', sa.String(45), nullable=False),
        sa.Column('hostname', sa.String(255), nullable=True),
        sa.Column('first_seen', sa.DateTime(), nullable=False),
        sa.Column('last_seen', sa.DateTime(), nullable=False),
        sa.Column('scan_id', sa.String(36), sa.ForeignKey('scan.id', ondelete='SET NULL'), nullable=True),
        sa.UniqueConstraint('project_id', 'ip', name='uq_host_project_ip'),
    )

    op.create_table(
        'service',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('host_id', sa.String(36), sa.ForeignKey('host.id', ondelete='CASCADE'), nullable=False),
        sa.Column('protocol', sa.String(10), nullable=False),
        sa.Column('port', sa.Integer(), nullable=False),
        sa.Column('state', sa.String(20), nullable=False),
        sa.Column('name', sa.String(100), nullable=True),
        sa.Column('product', sa.String(200), nullable=True),
        sa.Column('version', sa.String(200), nullable=True),
        sa.Column('first_seen', sa.DateTime(), nullable=False),
        sa.Column('last_seen', sa.DateTime(), nullable=False),
        sa.Column('scan_id', sa.String(36), sa.ForeignKey('scan.id', ondelete='SET NULL'), nullable=True),
        sa.UniqueConstraint('host_id', 'protocol', 'port', name='uq_service_host_proto_port'),
    )


def downgrade() -> None:
    op.drop_table('service')
    op.drop_table('host')
    op.drop_table('scan')
