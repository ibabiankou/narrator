"""Store sync_current_section and playback_rate in playback_progress

Revision ID: 114241e1a537
Revises: fa2b80a18af4
Create Date: 2025-12-17 14:57:49.599220

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '114241e1a537'
down_revision: Union[str, Sequence[str], None] = 'fa2b80a18af4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'playback_progress',
        sa.Column('sync_current_section', sa.Boolean)
    )
    op.add_column(
        'playback_progress',
        sa.Column('playback_rate', sa.Float)
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
