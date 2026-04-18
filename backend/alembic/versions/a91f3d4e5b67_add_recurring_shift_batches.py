"""add recurring shift batches

Revision ID: a91f3d4e5b67
Revises: f0e1d2c3b4a5
Create Date: 2026-04-18 13:15:00
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a91f3d4e5b67'
down_revision = 'f0e1d2c3b4a5'
branch_labels = None
depends_on = None


recurring_batch_status = sa.Enum('PREVIEW', 'CONFIRMED', 'FAILED', name='recurringbatchstatus')
recurring_item_decision_status = sa.Enum('PENDING', 'SKIPPED_CONFLICT', 'SKIPPED_DUPLICATE', 'CREATED', name='recurringitemdecisionstatus')


def upgrade() -> None:
    bind = op.get_bind()
    recurring_batch_status.create(bind, checkfirst=True)
    recurring_item_decision_status.create(bind, checkfirst=True)

    op.create_table(
        'recurring_shift_batches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('weekday', sa.Integer(), nullable=False),
        sa.Column('shift_label', sa.String(length=80), nullable=False),
        sa.Column('start_time', sa.String(length=5), nullable=False),
        sa.Column('end_time', sa.String(length=5), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('months_ahead', sa.Integer(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', recurring_batch_status, nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('confirmed_at', sa.DateTime(), nullable=True),
        sa.Column('summary_json', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recurring_shift_batches_end_date'), 'recurring_shift_batches', ['end_date'], unique=False)
    op.create_index(op.f('ix_recurring_shift_batches_id'), 'recurring_shift_batches', ['id'], unique=False)
    op.create_index(op.f('ix_recurring_shift_batches_start_date'), 'recurring_shift_batches', ['start_date'], unique=False)
    op.create_index(op.f('ix_recurring_shift_batches_user_id'), 'recurring_shift_batches', ['user_id'], unique=False)

    op.create_table(
        'recurring_shift_batch_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('batch_id', sa.Integer(), nullable=False),
        sa.Column('target_date', sa.Date(), nullable=False),
        sa.Column('start_datetime', sa.DateTime(), nullable=False),
        sa.Column('end_datetime', sa.DateTime(), nullable=False),
        sa.Column('existing_shift_id', sa.Integer(), nullable=True),
        sa.Column('conflict_status', sa.Boolean(), nullable=False),
        sa.Column('duplicate_status', sa.Boolean(), nullable=False),
        sa.Column('decision_status', recurring_item_decision_status, nullable=False),
        sa.Column('validation_messages', sa.Text(), nullable=True),
        sa.Column('created_shift_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['recurring_shift_batches.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_shift_id'], ['shifts.id']),
        sa.ForeignKeyConstraint(['existing_shift_id'], ['shifts.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recurring_shift_batch_items_batch_id'), 'recurring_shift_batch_items', ['batch_id'], unique=False)
    op.create_index(op.f('ix_recurring_shift_batch_items_id'), 'recurring_shift_batch_items', ['id'], unique=False)
    op.create_index(op.f('ix_recurring_shift_batch_items_target_date'), 'recurring_shift_batch_items', ['target_date'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_recurring_shift_batch_items_target_date'), table_name='recurring_shift_batch_items')
    op.drop_index(op.f('ix_recurring_shift_batch_items_id'), table_name='recurring_shift_batch_items')
    op.drop_index(op.f('ix_recurring_shift_batch_items_batch_id'), table_name='recurring_shift_batch_items')
    op.drop_table('recurring_shift_batch_items')

    op.drop_index(op.f('ix_recurring_shift_batches_user_id'), table_name='recurring_shift_batches')
    op.drop_index(op.f('ix_recurring_shift_batches_start_date'), table_name='recurring_shift_batches')
    op.drop_index(op.f('ix_recurring_shift_batches_id'), table_name='recurring_shift_batches')
    op.drop_index(op.f('ix_recurring_shift_batches_end_date'), table_name='recurring_shift_batches')
    op.drop_table('recurring_shift_batches')

    bind = op.get_bind()
    recurring_item_decision_status.drop(bind, checkfirst=True)
    recurring_batch_status.drop(bind, checkfirst=True)
