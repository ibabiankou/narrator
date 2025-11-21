"""Add columns to sections table to support speech generation

Revision ID: 8652554c18cb
Revises: 443cd901a111
Create Date: 2025-11-21 19:15:59.757419

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from api.models.db import SpeechStatus

# revision identifiers, used by Alembic.
revision: str = '8652554c18cb'
down_revision: Union[str, Sequence[str], None] = '443cd901a111'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'sections',
        sa.Column('phonemes', sa.String, nullable=True)
    )
    op.add_column(
        'sections',
        sa.Column('speech_status', sa.String, nullable=True, default=SpeechStatus.missing.value)
    )
    op.execute("update sections set speech_status = 'missing' where speech_status is null")
    op.alter_column('sections', 'speech_status', nullable=False)

    op.add_column(
        'sections',
        sa.Column('speech_file', sa.String, nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('sections', 'phonemes')
    op.drop_column('sections', 'speech_status')
    op.drop_column('sections', 'speech_file')
