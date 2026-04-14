"""Adiciona tabelas de importação de escala base

Revision ID: b3f1a2e4c8d0
Revises: 69a59d22a6f4
Create Date: 2026-04-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'b3f1a2e4c8d0'
down_revision = '69a59d22a6f4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'schedule_imports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('reference_period', sa.String(), nullable=True),
        sa.Column('source_description', sa.String(), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='importstatus'), nullable=False),
        sa.Column('total_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('valid_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('warning_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('invalid_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('duplicate_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('imported_by', sa.Integer(), nullable=False),
        sa.Column('confirmed_at', sa.DateTime(), nullable=True),
        sa.Column('confirmed_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['imported_by'], ['users.id']),
        sa.ForeignKeyConstraint(['confirmed_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_schedule_imports_id'), 'schedule_imports', ['id'], unique=False)

    op.create_table(
        'schedule_import_rows',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('import_id', sa.Integer(), nullable=False),
        sa.Column('row_number', sa.Integer(), nullable=False),
        sa.Column('raw_professional', sa.String(), nullable=True),
        sa.Column('raw_date', sa.String(), nullable=True),
        sa.Column('raw_start_time', sa.String(), nullable=True),
        sa.Column('raw_end_time', sa.String(), nullable=True),
        sa.Column('raw_total_hours', sa.String(), nullable=True),
        sa.Column('raw_observations', sa.String(), nullable=True),
        sa.Column('raw_source', sa.String(), nullable=True),
        sa.Column('agent_id', sa.Integer(), nullable=True),
        sa.Column('normalized_start', sa.DateTime(), nullable=True),
        sa.Column('normalized_end', sa.DateTime(), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('is_overnight', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_standard_shift', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('row_status', sa.Enum('VALID', 'WARNING', 'INVALID', name='rowstatus'), nullable=False),
        sa.Column('issues', sa.Text(), nullable=True),
        sa.Column('is_duplicate', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('has_overlap', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_shift_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['import_id'], ['schedule_imports.id']),
        sa.ForeignKeyConstraint(['agent_id'], ['users.id']),
        sa.ForeignKeyConstraint(['created_shift_id'], ['shifts.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_schedule_import_rows_id'), 'schedule_import_rows', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_schedule_import_rows_id'), table_name='schedule_import_rows')
    op.drop_table('schedule_import_rows')
    op.drop_index(op.f('ix_schedule_imports_id'), table_name='schedule_imports')
    op.drop_table('schedule_imports')
    # Remove enums (PostgreSQL only)
    op.execute("DROP TYPE IF EXISTS rowstatus")
    op.execute("DROP TYPE IF EXISTS importstatus")
