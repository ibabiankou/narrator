"""Drop books.shared

Revision ID: 15fe900e1c37
Revises: 53da1ebdb5e6
Create Date: 2026-03-31 18:45:40.148781

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '15fe900e1c37'
down_revision: Union[str, Sequence[str], None] = '53da1ebdb5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('books', 'shared')


def downgrade() -> None:
    """Downgrade schema."""
    pass
