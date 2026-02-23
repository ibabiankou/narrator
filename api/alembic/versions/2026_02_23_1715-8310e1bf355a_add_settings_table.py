"""Add settings table

Revision ID: 8310e1bf355a
Revises: 9f56bb851538
Create Date: 2026-02-23 17:15:27.156759

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '8310e1bf355a'
down_revision: Union[str, Sequence[str], None] = '9f56bb851538'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'settings',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('data', JSONB, nullable=False)
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
