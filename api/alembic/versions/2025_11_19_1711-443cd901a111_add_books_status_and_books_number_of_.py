"""Add books.status and books.number_of_pages columns

Revision ID: 443cd901a111
Revises: 9630bff6869d
Create Date: 2025-11-19 17:11:24.862985

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '443cd901a111'
down_revision: Union[str, Sequence[str], None] = '9630bff6869d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'books',
        sa.Column('status', sa.String, nullable=True)
    )
    op.execute("update books set status = 'ready' where status is null")
    op.alter_column('books', 'status', nullable=False)

    op.add_column(
        'books',
        sa.Column('number_of_pages', sa.Integer, nullable=True)
    )

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('books', 'number_of_pages')
    op.drop_column('books', 'status')
