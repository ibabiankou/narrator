"""Baseline

Revision ID: 322cfef0a985
Revises: 
Create Date: 2025-11-16 16:40:58.067631

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '322cfef0a985'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'temp_files',
        sa.Column('id', sa.UUID, primary_key=True),
        sa.Column('file_name', sa.String(), nullable=False),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('upload_time', sa.DateTime(), nullable=False),
    )

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('temp_files')
