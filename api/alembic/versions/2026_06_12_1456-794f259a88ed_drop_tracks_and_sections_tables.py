"""Drop tracks and sections tables

Revision ID: 794f259a88ed
Revises: d52b6e87ad5e
Create Date: 2026-06-12 14:56:30.854142

"""
from alembic import op
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '794f259a88ed'
down_revision: Union[str, Sequence[str], None] = 'd52b6e87ad5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_table('audio_tracks')
    op.drop_table('sections')


def downgrade() -> None:
    """Downgrade schema."""
    pass
