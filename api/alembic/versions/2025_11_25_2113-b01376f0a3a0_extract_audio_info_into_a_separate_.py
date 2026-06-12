"""Extract audio info into a separate entity

Revision ID: b01376f0a3a0
Revises: 8652554c18cb
Create Date: 2025-11-25 21:13:25.997660

"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = 'b01376f0a3a0'
down_revision: Union[str, Sequence[str], None] = '8652554c18cb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass

def downgrade() -> None:
    """Downgrade schema."""
    # Ignore downgrades for the time being. Bother about them once the service is live.
    pass
