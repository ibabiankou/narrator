"""Add metadata columns to books table.

Revision ID: 47b73e59bdfa
Revises: 062a6d61a136
Create Date: 2026-04-24 15:36:37.985469

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

# revision identifiers, used by Alembic.
revision: str = '47b73e59bdfa'
down_revision: Union[str, Sequence[str], None] = '062a6d61a136'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('books', sa.Column('series', sa.String, nullable=True))
    op.add_column('books', sa.Column('description', sa.String, nullable=True))
    op.add_column('books', sa.Column('authors', ARRAY(sa.String), nullable=True))
    op.add_column('books', sa.Column('isbns', ARRAY(sa.String), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('books', 'series')
    op.drop_column('books', 'description')
    op.drop_column('books', 'authors')
    op.drop_column('books', 'isbns')
