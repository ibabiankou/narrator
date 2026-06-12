"""Extend procurement.epub_files; Add procurement.metadata_ids

Revision ID: d22295a789e5
Revises: 19f924674ea3
Create Date: 2026-05-12 02:32:02.808065

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = 'd22295a789e5'
down_revision: Union[str, Sequence[str], None] = '19f924674ea3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('metadata_ids',
                    sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
                    sa.Column('source_file', sa.Integer(), nullable=False),
                    sa.Column('value', sa.String(), unique=True, nullable=False),
                    sa.ForeignKeyConstraint(['source_file'], ['procurement.epub_files.id'], ),
                    schema='procurement'
                    )

    op.add_column('epub_files', sa.Column('raw_metadata', JSONB, nullable=False),
                  schema='procurement')
    op.add_column('epub_files', sa.Column('id_matches', JSONB, nullable=False),
                  schema='procurement')
    op.alter_column('epub_files', 'file_name',
                    existing_type=sa.VARCHAR(),
                    nullable=False,
                    schema='procurement')


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('epub_files', 'file_name',
                    existing_type=sa.VARCHAR(),
                    nullable=True,
                    schema='procurement')
    op.drop_column('epub_files', 'id_matches', schema='procurement')
    op.drop_column('epub_files', 'raw_metadata', schema='procurement')
    op.drop_table('metadata_ids', schema='procurement')
