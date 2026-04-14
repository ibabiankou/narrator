"""Add books.cover

Revision ID: 996218ac3cf4
Revises: 15fe900e1c37
Create Date: 2026-04-14 19:08:33.756753

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '996218ac3cf4'
down_revision: Union[str, Sequence[str], None] = '15fe900e1c37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('books', sa.Column('cover', sa.String, nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('books', 'cover')
