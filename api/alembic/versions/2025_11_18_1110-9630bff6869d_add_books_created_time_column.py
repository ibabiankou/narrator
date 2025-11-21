"""Add books.created_time column

Revision ID: 9630bff6869d
Revises: d8df8166266c
Create Date: 2025-11-18 11:10:18.637023

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9630bff6869d'
down_revision: Union[str, Sequence[str], None] = 'd8df8166266c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'books',
        sa.Column('created_time', sa.DateTime, nullable=True)
    )
    op.execute("update books set created_time = now() where created_time is null")
    op.alter_column('books', 'created_time', nullable=False)

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('books', 'created_time')
