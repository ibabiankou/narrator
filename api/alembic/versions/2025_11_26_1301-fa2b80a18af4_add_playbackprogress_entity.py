"""Add PlaybackProgress entity

Revision ID: fa2b80a18af4
Revises: b01376f0a3a0
Create Date: 2025-11-26 13:01:15.915133

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fa2b80a18af4'
down_revision: Union[str, Sequence[str], None] = 'b01376f0a3a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'playback_progress',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('book_id', sa.UUID, sa.ForeignKey('books.id'), nullable=False, unique=True),
        sa.Column('section_id', sa.Integer, sa.ForeignKey('sections.id'), nullable=False),
        sa.Column('section_progress', sa.Float, nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
