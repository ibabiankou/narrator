"""Add books table

Revision ID: b33959ce8d24
Revises: 322cfef0a985
Create Date: 2025-11-16 23:02:31.027242

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b33959ce8d24'
down_revision: Union[str, Sequence[str], None] = '322cfef0a985'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'books',
        sa.Column('id', sa.UUID, primary_key=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('file_name', sa.String(), nullable=False),
    )

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('books')
