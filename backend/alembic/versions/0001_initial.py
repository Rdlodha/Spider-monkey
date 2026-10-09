"""initial

Revision ID: 0001
Revises: 
Create Date: 2026-10-07
"""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table('project',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('authorized_ack_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_table('target',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('project.id', ondelete='CASCADE'), nullable=False),
        sa.Column('value', sa.String(500), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_table('audit_log',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('ts', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('actor', sa.String(50), nullable=False, server_default='local'),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('target', sa.String(500), nullable=True),
        sa.Column('tool', sa.String(100), nullable=True),
        sa.Column('result', sa.String(100), nullable=True),
    )

def downgrade() -> None:
    op.drop_table('audit_log')
    op.drop_table('target')
    op.drop_table('project')
