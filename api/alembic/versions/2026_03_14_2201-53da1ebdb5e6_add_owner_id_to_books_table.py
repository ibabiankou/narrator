"""Add owner_id to books table

Revision ID: 53da1ebdb5e6
Revises: 8f8c92f43c30
Create Date: 2026-03-14 22:01:12.522333

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '53da1ebdb5e6'
down_revision: Union[str, Sequence[str], None] = '8f8c92f43c30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('books', sa.Column('owner_id', sa.UUID, nullable=True))
    op.execute("update books set owner_id = '2a1561b8-a8d8-4a83-baa1-8d804957f882' where 1=1")
    op.alter_column('books', 'owner_id', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    pass
