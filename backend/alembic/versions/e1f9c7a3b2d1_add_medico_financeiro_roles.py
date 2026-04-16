"""Adiciona roles MEDICO e FINANCEIRO no enum userrole

Revision ID: e1f9c7a3b2d1
Revises: d4a8f1c2e9b0
Create Date: 2026-04-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "e1f9c7a3b2d1"
down_revision: Union[str, None] = "d4a8f1c2e9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'MEDICO'")
        op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'FINANCEIRO'")


def downgrade() -> None:
    # PostgreSQL não remove valores de enum sem recriação de tipo.
    # Mantido sem-op para preservar compatibilidade com dados existentes.
    pass
