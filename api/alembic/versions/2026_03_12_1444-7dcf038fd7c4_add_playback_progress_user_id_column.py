"""Add playback_progress.user_id column

Revision ID: 7dcf038fd7c4
Revises: 92b34bd1e6f1
Create Date: 2026-03-12 14:44:34.723038

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7dcf038fd7c4'
down_revision: Union[str, Sequence[str], None] = '92b34bd1e6f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('playback_progress', sa.Column('user_id', sa.UUID, nullable=True))
    op.execute("update playback_progress set user_id = '2a1561b8-a8d8-4a83-baa1-8d804957f882' where 1=1")
    op.alter_column('playback_progress', 'user_id', nullable=False)
    op.alter_column('playback_progress', 'book_id', unique=False)

    op.create_index('idx_playback_progress_user_book',
                    'playback_progress',
                    ['user_id', 'book_id'],
                    unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    pass
