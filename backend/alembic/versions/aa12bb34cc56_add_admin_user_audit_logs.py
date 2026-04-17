"""add admin user audit logs table

Revision ID: aa12bb34cc56
Revises: f5a1b9d3c7e0
Create Date: 2026-04-17
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'aa12bb34cc56'
down_revision = 'f5a1b9d3c7e0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'admin_user_audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('admin_user_id', sa.Integer(), nullable=False),
        sa.Column('target_user_id', sa.Integer(), nullable=False),
        sa.Column('change_summary', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_admin_user_audit_logs_action'), 'admin_user_audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_admin_user_audit_logs_admin_user_id'), 'admin_user_audit_logs', ['admin_user_id'], unique=False)
    op.create_index(op.f('ix_admin_user_audit_logs_target_user_id'), 'admin_user_audit_logs', ['target_user_id'], unique=False)
    op.create_index(op.f('ix_admin_user_audit_logs_created_at'), 'admin_user_audit_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_admin_user_audit_logs_id'), 'admin_user_audit_logs', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_admin_user_audit_logs_id'), table_name='admin_user_audit_logs')
    op.drop_index(op.f('ix_admin_user_audit_logs_created_at'), table_name='admin_user_audit_logs')
    op.drop_index(op.f('ix_admin_user_audit_logs_target_user_id'), table_name='admin_user_audit_logs')
    op.drop_index(op.f('ix_admin_user_audit_logs_admin_user_id'), table_name='admin_user_audit_logs')
    op.drop_index(op.f('ix_admin_user_audit_logs_action'), table_name='admin_user_audit_logs')
    op.drop_table('admin_user_audit_logs')
