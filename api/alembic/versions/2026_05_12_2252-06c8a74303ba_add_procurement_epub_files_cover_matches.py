"""Add procurement.epub_files.cover_matches

Revision ID: 06c8a74303ba
Revises: 47601eac6071
Create Date: 2026-05-12 22:52:17.845128

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = '06c8a74303ba'
down_revision: Union[str, Sequence[str], None] = '47601eac6071'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('epub_files', sa.Column('cover_matches', JSONB, nullable=False),
                  schema='procurement')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('epub_files', 'cover_matches', schema='procurement')
