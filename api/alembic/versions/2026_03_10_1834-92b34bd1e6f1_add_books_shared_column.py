"""Add books.shared column

Revision ID: 92b34bd1e6f1
Revises: 8310e1bf355a
Create Date: 2026-03-10 18:34:40.236563

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '92b34bd1e6f1'
down_revision: Union[str, Sequence[str], None] = '8310e1bf355a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('books', sa.Column('shared', sa.Boolean, nullable=True))
    op.execute("update books set shared = false where 1=1")
    op.alter_column('books', 'shared', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    pass
