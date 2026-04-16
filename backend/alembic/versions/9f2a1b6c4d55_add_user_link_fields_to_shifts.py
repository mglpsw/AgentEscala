"""add user linkage fields to shifts

Revision ID: 9f2a1b6c4d55
Revises: e1f9c7a3b2d1
Create Date: 2026-04-16 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9f2a1b6c4d55'
down_revision: Union[str, None] = 'e1f9c7a3b2d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('shifts', sa.Column('user_id', sa.Integer(), nullable=True))
    op.add_column('shifts', sa.Column('legacy_agent_name', sa.String(), nullable=True))
    op.create_index(op.f('ix_shifts_user_id'), 'shifts', ['user_id'], unique=False)
    op.create_foreign_key('fk_shifts_user_id_users', 'shifts', 'users', ['user_id'], ['id'])

    op.execute('UPDATE shifts SET user_id = agent_id WHERE user_id IS NULL')


def downgrade() -> None:
    op.drop_constraint('fk_shifts_user_id_users', 'shifts', type_='foreignkey')
    op.drop_index(op.f('ix_shifts_user_id'), table_name='shifts')
    op.drop_column('shifts', 'legacy_agent_name')
    op.drop_column('shifts', 'user_id')
