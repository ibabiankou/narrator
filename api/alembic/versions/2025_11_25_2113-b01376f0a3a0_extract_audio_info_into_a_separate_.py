"""Extract audio info into a separate entity

Revision ID: b01376f0a3a0
Revises: 8652554c18cb
Create Date: 2025-11-25 21:13:25.997660

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from api.models.db import AudioStatus

# revision identifiers, used by Alembic.
revision: str = 'b01376f0a3a0'
down_revision: Union[str, Sequence[str], None] = '8652554c18cb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'audio_tracks',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('book_id', sa.UUID, sa.ForeignKey('books.id'), nullable=False),
        sa.Column('section_id', sa.Integer, sa.ForeignKey('sections.id'), nullable=False, unique=True),
        sa.Column('playlist_order', sa.Integer, nullable=False),

        sa.Column('status', sa.String, nullable=False, default=AudioStatus.missing.value),

        sa.Column('file_name', sa.String, nullable=True),
        sa.Column('duration', sa.Float, nullable=True),
    )

    # Not moving data, starting from a clean state...

    # Drop other columns
    op.drop_column('sections', 'speech_status')
    op.drop_column('sections', 'speech_file')

def downgrade() -> None:
    """Downgrade schema."""
    # Ignore downgrades for the time being. Bother about them once the service is live.
    pass
