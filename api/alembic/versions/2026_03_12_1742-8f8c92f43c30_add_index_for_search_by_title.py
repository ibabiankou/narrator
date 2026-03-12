"""Add index for search by title

Revision ID: 8f8c92f43c30
Revises: 9e2ca470a764
Create Date: 2026-03-12 17:42:18.307882

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f8c92f43c30'
down_revision: Union[str, Sequence[str], None] = '9e2ca470a764'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')

    op.create_index(
        'idx_books_title_trgm',
        'books',
        ['title'],
        postgresql_using='gin',
        postgresql_ops={'title': 'gin_trgm_ops'}
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
