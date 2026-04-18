"""Merge admin audit and shift request migration heads.

Revision ID: f0e1d2c3b4a5
Revises: aa12bb34cc56, d7c1f4ea9a20
Create Date: 2026-04-18 07:16:00.000000
"""

from typing import Sequence, Union


revision: str = "f0e1d2c3b4a5"
down_revision: Union[str, tuple[str, str], None] = ("aa12bb34cc56", "d7c1f4ea9a20")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
