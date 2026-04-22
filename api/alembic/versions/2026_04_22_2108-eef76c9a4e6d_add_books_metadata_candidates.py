"""Add books.metadata_candidates

Revision ID: eef76c9a4e6d
Revises: 996218ac3cf4
Create Date: 2026-04-22 21:08:19.750727

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = 'eef76c9a4e6d'
down_revision: Union[str, Sequence[str], None] = '996218ac3cf4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('books', sa.Column('metadata_candidates', JSONB, nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('books', 'metadata_candidates')
