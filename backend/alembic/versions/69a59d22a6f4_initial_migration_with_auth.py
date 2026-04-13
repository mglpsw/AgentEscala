"""Migração inicial com autenticação

Revision ID: 69a59d22a6f4
Revises:
Create Date: 2026-04-13 19:43:30.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Identificadores da revisão, usados pelo Alembic.
revision = '69a59d22a6f4'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### comandos gerados automaticamente pelo Alembic - ajuste se necessário ###
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('hashed_password', sa.String(), nullable=False),
    sa.Column('role', sa.Enum('ADMIN', 'AGENT', name='userrole'), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_table('shifts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('agent_id', sa.Integer(), nullable=False),
    sa.Column('start_time', sa.DateTime(), nullable=False),
    sa.Column('end_time', sa.DateTime(), nullable=False),
    sa.Column('title', sa.String(), nullable=True),
    sa.Column('description', sa.String(), nullable=True),
    sa.Column('location', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['agent_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_shifts_id'), 'shifts', ['id'], unique=False)
    op.create_table('swap_requests',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('requester_id', sa.Integer(), nullable=False),
    sa.Column('target_agent_id', sa.Integer(), nullable=False),
    sa.Column('origin_shift_id', sa.Integer(), nullable=False),
    sa.Column('target_shift_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED', name='swapstatus'), nullable=False),
    sa.Column('reason', sa.String(), nullable=True),
    sa.Column('admin_notes', sa.String(), nullable=True),
    sa.Column('reviewed_by', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['origin_shift_id'], ['shifts.id'], ),
    sa.ForeignKeyConstraint(['requester_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['target_agent_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['target_shift_id'], ['shifts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_swap_requests_id'), 'swap_requests', ['id'], unique=False)
    # ### fim dos comandos Alembic ###


def downgrade() -> None:
    # ### comandos gerados automaticamente pelo Alembic - ajuste se necessário ###
    op.drop_index(op.f('ix_swap_requests_id'), table_name='swap_requests')
    op.drop_table('swap_requests')
    op.drop_index(op.f('ix_shifts_id'), table_name='shifts')
    op.drop_table('shifts')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    # ### fim dos comandos Alembic ###
