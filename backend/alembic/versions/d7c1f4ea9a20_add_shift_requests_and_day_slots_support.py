"""add shift requests table

Revision ID: d7c1f4ea9a20
Revises: c2a7e8d91b11
Create Date: 2026-04-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = 'd7c1f4ea9a20'
down_revision = 'c2a7e8d91b11'
branch_labels = None
depends_on = None


shift_request_status = postgresql.ENUM(
    'PENDING_TARGET',
    'PENDING_ADMIN',
    'APPROVED',
    'REJECTED',
    'CANCELLED',
    name='shiftrequeststatus',
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    shift_request_status.create(bind, checkfirst=True)

    op.create_table(
        'shift_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('requester_id', sa.Integer(), nullable=False),
        sa.Column('target_user_id', sa.Integer(), nullable=True),
        sa.Column('target_shift_id', sa.Integer(), nullable=True),
        sa.Column('requested_date', sa.Date(), nullable=False),
        sa.Column('shift_period', sa.String(length=40), nullable=False),
        sa.Column('note', sa.String(), nullable=True),
        sa.Column('status', shift_request_status, nullable=False, server_default='PENDING_TARGET'),
        sa.Column('target_response_note', sa.String(), nullable=True),
        sa.Column('admin_notes', sa.String(), nullable=True),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['requester_id'], ['users.id']),
        sa.ForeignKeyConstraint(['target_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['target_shift_id'], ['shifts.id']),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_shift_requests_id'), 'shift_requests', ['id'], unique=False)
    op.create_index(op.f('ix_shift_requests_requester_id'), 'shift_requests', ['requester_id'], unique=False)
    op.create_index(op.f('ix_shift_requests_target_user_id'), 'shift_requests', ['target_user_id'], unique=False)
    op.create_index(op.f('ix_shift_requests_target_shift_id'), 'shift_requests', ['target_shift_id'], unique=False)
    op.create_index(op.f('ix_shift_requests_requested_date'), 'shift_requests', ['requested_date'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_shift_requests_requested_date'), table_name='shift_requests')
    op.drop_index(op.f('ix_shift_requests_target_shift_id'), table_name='shift_requests')
    op.drop_index(op.f('ix_shift_requests_target_user_id'), table_name='shift_requests')
    op.drop_index(op.f('ix_shift_requests_requester_id'), table_name='shift_requests')
    op.drop_index(op.f('ix_shift_requests_id'), table_name='shift_requests')
    op.drop_table('shift_requests')

    bind = op.get_bind()
    shift_request_status.drop(bind, checkfirst=True)
