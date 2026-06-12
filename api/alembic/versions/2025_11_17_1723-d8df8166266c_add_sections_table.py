"""Add sections table

Revision ID: d8df8166266c
Revises: b33959ce8d24
Create Date: 2025-11-17 17:23:07.653739

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = 'd8df8166266c'
down_revision: Union[str, Sequence[str], None] = 'b33959ce8d24'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
