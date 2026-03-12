"""Add settings.user_id column

Revision ID: 9e2ca470a764
Revises: 7dcf038fd7c4
Create Date: 2026-03-12 16:52:58.449226

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9e2ca470a764'
down_revision: Union[str, Sequence[str], None] = '7dcf038fd7c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('settings', sa.Column('user_id', sa.UUID, nullable=True))
    op.execute("update settings set user_id = '2a1561b8-a8d8-4a83-baa1-8d804957f882' where 1=1")
    op.alter_column('settings', 'user_id', nullable=False)

    op.create_index('idx_settings_user_kind',
                    'settings',
                    ['user_id', 'kind'],
                    unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    pass
