"""add future shift requests table

Revision ID: c2a7e8d91b11
Revises: f5a1b9d3c7e0
Create Date: 2026-04-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = 'c2a7e8d91b11'
down_revision = 'f5a1b9d3c7e0'
branch_labels = None
depends_on = None


future_request_status = postgresql.ENUM(
    'ACTIVE',
    'CANCELLED',
    name='futureshiftrequeststatus',
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    future_request_status.create(bind, checkfirst=True)

    op.create_table(
        'future_shift_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('requested_date', sa.Date(), nullable=False),
        sa.Column('shift_period', sa.String(length=40), nullable=False),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('status', future_request_status, nullable=False, server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_future_shift_requests_id'), 'future_shift_requests', ['id'], unique=False)
    op.create_index(op.f('ix_future_shift_requests_requested_date'), 'future_shift_requests', ['requested_date'], unique=False)
    op.create_index(op.f('ix_future_shift_requests_user_id'), 'future_shift_requests', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_future_shift_requests_user_id'), table_name='future_shift_requests')
    op.drop_index(op.f('ix_future_shift_requests_requested_date'), table_name='future_shift_requests')
    op.drop_index(op.f('ix_future_shift_requests_id'), table_name='future_shift_requests')
    op.drop_table('future_shift_requests')

    bind = op.get_bind()
    future_request_status.drop(bind, checkfirst=True)
