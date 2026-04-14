"""add ocr_imports table

Revision ID: b3dee2c3a703
Revises: b3f1a2e4c8d0
Create Date: 2026-04-14 02:13:43.773602

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# Identificadores de revisão, usados pelo Alembic.
revision: str = 'b3dee2c3a703'
down_revision: Union[str, None] = 'b3f1a2e4c8d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    is_pg = op.get_bind().dialect.name == 'postgresql'

    id_type   = postgresql.UUID(as_uuid=True) if is_pg else sa.String(36)

    def json_type():
        return postgresql.JSONB(astext_type=sa.Text()) if is_pg else sa.JSON()
    op.create_table(
        'ocr_imports',
        sa.Column('id', id_type, nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='draft'),
        sa.Column('file_name', sa.String(), nullable=True),
        sa.Column('file_type', sa.String(), nullable=True),
        sa.Column('raw_payload', json_type(), nullable=True),
        sa.Column('parsed_rows', json_type(), nullable=True),
        sa.Column('errors', json_type(), nullable=True),
        sa.Column('action_log', json_type(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('confirmed_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('confirmed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['confirmed_by'], ['users.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('ocr_imports')
