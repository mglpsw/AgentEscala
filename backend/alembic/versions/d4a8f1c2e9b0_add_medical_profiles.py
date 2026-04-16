"""Adiciona perfis médicos e sinalizador administrativo

Revision ID: d4a8f1c2e9b0
Revises: 187f6c14d777
Create Date: 2026-04-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Identificadores de revisão, usados pelo Alembic.
revision: str = "d4a8f1c2e9b0"
down_revision: Union[str, None] = "187f6c14d777"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UF_VALUES = (
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
    "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
    "RS", "RO", "RR", "SC", "SP", "SE", "TO",
)


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "medical_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("nome_completo", sa.String(), nullable=False),
        sa.Column("cpf", sa.String(length=11), nullable=False),
        sa.Column("crm_numero", sa.String(), nullable=False),
        sa.Column("crm_uf", sa.Enum(*UF_VALUES, name="ufenum"), nullable=False),
        sa.Column("data_nascimento", sa.Date(), nullable=False),
        sa.Column("cartao_nacional_saude", sa.String(), nullable=False),
        sa.Column("email_profissional", sa.String(), nullable=False),
        sa.Column("telefone", sa.String(), nullable=True),
        sa.Column("endereco", sa.Text(), nullable=True),
        sa.Column("rg", sa.String(), nullable=True),
        sa.Column("rg_orgao_emissor", sa.String(), nullable=True),
        sa.Column("rg_data_emissao", sa.Date(), nullable=True),
        sa.Column("crm_data_emissao", sa.Date(), nullable=True),
        sa.Column("arquivo_vacinacao", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("crm_numero", "crm_uf", name="uq_medical_profiles_crm_numero_uf"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_medical_profiles_id"), "medical_profiles", ["id"], unique=False)
    op.create_index(op.f("ix_medical_profiles_cpf"), "medical_profiles", ["cpf"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_medical_profiles_cpf"), table_name="medical_profiles")
    op.drop_index(op.f("ix_medical_profiles_id"), table_name="medical_profiles")
    op.drop_table("medical_profiles")
    op.drop_column("users", "is_admin")
    op.execute("DROP TYPE IF EXISTS ufenum")
