"""Store bytes in audio_track

Revision ID: 51f3e125587f
Revises: 114241e1a537
Create Date: 2026-01-14 13:44:14.594673

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '51f3e125587f'
down_revision: Union[str, Sequence[str], None] = '114241e1a537'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'audio_tracks',
        sa.Column('bytes', sa.Integer, nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
