"""Drop temp_files table

Revision ID: 2d8dad9aae9e
Revises: 47b73e59bdfa
Create Date: 2026-05-04 14:09:07.215672

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2d8dad9aae9e'
down_revision: Union[str, Sequence[str], None] = '47b73e59bdfa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_table('temp_files')


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        'temp_files',
        sa.Column('id', sa.UUID, primary_key=True),
        sa.Column('file_name', sa.String(), nullable=False),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('upload_time', sa.DateTime(), nullable=False),
    )
