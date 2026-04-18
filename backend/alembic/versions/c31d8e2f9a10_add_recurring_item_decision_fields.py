"""add recurring item decision fields

Revision ID: c31d8e2f9a10
Revises: a91f3d4e5b67
Create Date: 2026-04-18 14:10:00
"""
from alembic import op
import sqlalchemy as sa


revision = 'c31d8e2f9a10'
down_revision = 'a91f3d4e5b67'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('recurring_shift_batch_items', sa.Column('decision_action', sa.String(length=32), nullable=True))
    op.add_column('recurring_shift_batch_items', sa.Column('decision_notes', sa.Text(), nullable=True))
    op.add_column('recurring_shift_batch_items', sa.Column('decided_by', sa.Integer(), nullable=True))
    op.add_column('recurring_shift_batch_items', sa.Column('decided_at', sa.DateTime(), nullable=True))
    op.create_foreign_key(None, 'recurring_shift_batch_items', 'users', ['decided_by'], ['id'])


def downgrade() -> None:
    op.drop_constraint(None, 'recurring_shift_batch_items', type_='foreignkey')
    op.drop_column('recurring_shift_batch_items', 'decided_at')
    op.drop_column('recurring_shift_batch_items', 'decided_by')
    op.drop_column('recurring_shift_batch_items', 'decision_notes')
    op.drop_column('recurring_shift_batch_items', 'decision_action')
