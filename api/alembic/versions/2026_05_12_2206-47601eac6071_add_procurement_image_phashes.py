"""Add procurement.image_phashes

Revision ID: 47601eac6071
Revises: d98f86021ade
Create Date: 2026-05-12 22:06:25.030495

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import BIT

# revision identifiers, used by Alembic.
revision: str = '47601eac6071'
down_revision: Union[str, Sequence[str], None] = 'd98f86021ade'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('image_phashes',
                    sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
                    sa.Column('source_file', sa.Integer(), nullable=False),
                    sa.Column('image_name', sa.String(), nullable=False),
                    sa.Column('phash', BIT(length=64), nullable=False),
                    sa.ForeignKeyConstraint(['source_file'], ['procurement.epub_files.id'], ),
                    schema='procurement'
                    )

    op.create_index(
        'idx_phash_band_1',
        'image_phashes',
        [sa.text("substring(phash from 1 for 16)")],
        postgresql_using='btree',
        schema='procurement'
    )
    op.create_index(
        'idx_phash_band_2',
        'image_phashes',
        [sa.text("substring(phash from 17 for 16)")],
        postgresql_using='btree',
        schema='procurement'
    )
    op.create_index(
        'idx_phash_band_3',
        'image_phashes',
        [sa.text("substring(phash from 33 for 16)")],
        postgresql_using='btree',
        schema='procurement'
    )
    op.create_index(
        'idx_phash_band_4',
        'image_phashes',
        [sa.text("substring(phash from 49 for 16)")],
        postgresql_using='btree',
        schema='procurement'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_phash_band_1', table_name='image_phashes', schema='procurement')
    op.drop_index('idx_phash_band_2', table_name='image_phashes', schema='procurement')
    op.drop_index('idx_phash_band_3', table_name='image_phashes', schema='procurement')
    op.drop_index('idx_phash_band_4', table_name='image_phashes', schema='procurement')
    op.drop_table('image_phashes', schema='procurement')
