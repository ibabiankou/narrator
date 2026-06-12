"""Add columns to sections table to support speech generation

Revision ID: 8652554c18cb
Revises: 443cd901a111
Create Date: 2025-11-21 19:15:59.757419

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '8652554c18cb'
down_revision: Union[str, Sequence[str], None] = '443cd901a111'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
