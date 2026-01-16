"""Store progress data in jsonb column

Revision ID: 9f56bb851538
Revises: 51f3e125587f
Create Date: 2026-01-16 00:51:20.256298

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = '9f56bb851538'
down_revision: Union[str, Sequence[str], None] = '51f3e125587f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("delete from playback_progress where 1 = 1")
    op.drop_column('playback_progress', 'section_id')
    op.drop_column('playback_progress', 'section_progress')
    op.drop_column('playback_progress', 'sync_current_section')
    op.drop_column('playback_progress', 'playback_rate')

    op.add_column('playback_progress', sa.Column('data', JSONB, nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    pass
