"""Make books.title nullable

Revision ID: 062a6d61a136
Revises: eef76c9a4e6d
Create Date: 2026-04-22 21:38:15.688584

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '062a6d61a136'
down_revision: Union[str, Sequence[str], None] = 'eef76c9a4e6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('books', 'title', nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('books', 'title', nullable=False)
