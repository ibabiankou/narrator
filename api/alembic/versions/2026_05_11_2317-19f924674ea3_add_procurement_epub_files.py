"""Add procurement.epub_files

Revision ID: 19f924674ea3
Revises: 7ae176a85410
Create Date: 2026-05-11 23:17:17.314115

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '19f924674ea3'
down_revision: Union[str, Sequence[str], None] = '7ae176a85410'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('epub_files',
                    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
                    sa.Column('file_name', sa.String(), nullable=True),
                    sa.Column('file_hash', sa.String(), nullable=False),
                    sa.Column('file_size_bytes', sa.Integer(), nullable=False),
                    sa.PrimaryKeyConstraint('id'),
                    schema='procurement'
                    )
    op.create_index('idx_epub_files_file_hash',
                    'epub_files',
                    ['file_hash'],
                    unique=True,
                    schema='procurement'
                    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('epub_files', schema='procurement')
