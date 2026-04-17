"""phase 4.5 ocr hardening and user profile/avatar

Revision ID: f5a1b9d3c7e0
Revises: 9f2a1b6c4d55
Create Date: 2026-04-17
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f5a1b9d3c7e0'
down_revision = '9f2a1b6c4d55'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('phone', sa.String(), nullable=True))
    op.add_column('users', sa.Column('specialty', sa.String(), nullable=True))
    op.add_column('users', sa.Column('profile_notes', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('avatar_path', sa.String(), nullable=True))

    op.add_column('schedule_import_rows', sa.Column('confidence_score', sa.Float(), nullable=True))
    op.add_column('schedule_import_rows', sa.Column('parse_status', sa.String(), nullable=False, server_default='ok'))
    op.add_column('schedule_import_rows', sa.Column('match_status', sa.String(), nullable=False, server_default='unmatched'))
    op.add_column('schedule_import_rows', sa.Column('validation_status', sa.String(), nullable=False, server_default='pending'))

    op.add_column('ocr_imports', sa.Column('source_origin', sa.String(), nullable=True))
    op.add_column('ocr_imports', sa.Column('processing_strategy', sa.String(), nullable=True))
    op.add_column('ocr_imports', sa.Column('extracted_lines', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('ocr_imports', sa.Column('valid_lines', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('ocr_imports', sa.Column('ambiguous_lines', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('ocr_imports', sa.Column('conflict_lines', sa.Integer(), nullable=False, server_default='0'))

def downgrade() -> None:
    op.drop_column('ocr_imports', 'conflict_lines')
    op.drop_column('ocr_imports', 'ambiguous_lines')
    op.drop_column('ocr_imports', 'valid_lines')
    op.drop_column('ocr_imports', 'extracted_lines')
    op.drop_column('ocr_imports', 'processing_strategy')
    op.drop_column('ocr_imports', 'source_origin')

    op.drop_column('schedule_import_rows', 'validation_status')
    op.drop_column('schedule_import_rows', 'match_status')
    op.drop_column('schedule_import_rows', 'parse_status')
    op.drop_column('schedule_import_rows', 'confidence_score')

    op.drop_column('users', 'avatar_path')
    op.drop_column('users', 'profile_notes')
    op.drop_column('users', 'specialty')
    op.drop_column('users', 'phone')
