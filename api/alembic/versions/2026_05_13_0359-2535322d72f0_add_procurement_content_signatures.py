"""Add procurement.content_signatures

Revision ID: 2535322d72f0
Revises: 06c8a74303ba
Create Date: 2026-05-13 03:59:07.408802

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = '2535322d72f0'
down_revision: Union[str, Sequence[str], None] = '06c8a74303ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('content_signatures',
                    sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
                    sa.Column('source_file', sa.Integer(), nullable=False),
                    sa.Column('full_signature', postgresql.ARRAY(sa.BigInteger()), nullable=False),
                    sa.Column('band1', postgresql.ARRAY(sa.BigInteger()), nullable=False),
                    sa.Column('band2', postgresql.ARRAY(sa.BigInteger()), nullable=False),
                    sa.Column('band3', postgresql.ARRAY(sa.BigInteger()), nullable=False),
                    sa.Column('band4', postgresql.ARRAY(sa.BigInteger()), nullable=False),
                    sa.Column('band5', postgresql.ARRAY(sa.BigInteger()), nullable=False),
                    sa.Column('band6', postgresql.ARRAY(sa.BigInteger()), nullable=False),
                    sa.Column('band7', postgresql.ARRAY(sa.BigInteger()), nullable=False),
                    sa.Column('band8', postgresql.ARRAY(sa.BigInteger()), nullable=False),
                    sa.ForeignKeyConstraint(['source_file'], ['procurement.epub_files.id'], ),
                    schema='procurement'
                    )
    op.create_index(op.f('ix_procurement_content_signatures_band1'), 'content_signatures', ['band1'], unique=False,
                    schema='procurement')
    op.create_index(op.f('ix_procurement_content_signatures_band2'), 'content_signatures', ['band2'], unique=False,
                    schema='procurement')
    op.create_index(op.f('ix_procurement_content_signatures_band3'), 'content_signatures', ['band3'], unique=False,
                    schema='procurement')
    op.create_index(op.f('ix_procurement_content_signatures_band4'), 'content_signatures', ['band4'], unique=False,
                    schema='procurement')
    op.create_index(op.f('ix_procurement_content_signatures_band5'), 'content_signatures', ['band5'], unique=False,
                    schema='procurement')
    op.create_index(op.f('ix_procurement_content_signatures_band6'), 'content_signatures', ['band6'], unique=False,
                    schema='procurement')
    op.create_index(op.f('ix_procurement_content_signatures_band7'), 'content_signatures', ['band7'], unique=False,
                    schema='procurement')
    op.create_index(op.f('ix_procurement_content_signatures_band8'), 'content_signatures', ['band8'], unique=False,
                    schema='procurement')
    op.add_column('epub_files', sa.Column('content_matches', JSONB, nullable=False),
                  schema='procurement')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('epub_files', 'content_matches', schema='procurement')
    op.drop_index(op.f('ix_procurement_content_signatures_band8'),
                  table_name='content_signatures',
                  schema='procurement')
    op.drop_index(op.f('ix_procurement_content_signatures_band7'),
                  table_name='content_signatures',
                  schema='procurement')
    op.drop_index(op.f('ix_procurement_content_signatures_band6'),
                  table_name='content_signatures',
                  schema='procurement')
    op.drop_index(op.f('ix_procurement_content_signatures_band5'),
                  table_name='content_signatures',
                  schema='procurement')
    op.drop_index(op.f('ix_procurement_content_signatures_band4'),
                  table_name='content_signatures',
                  schema='procurement')
    op.drop_index(op.f('ix_procurement_content_signatures_band3'),
                  table_name='content_signatures',
                  schema='procurement')
    op.drop_index(op.f('ix_procurement_content_signatures_band2'),
                  table_name='content_signatures',
                  schema='procurement')
    op.drop_index(op.f('ix_procurement_content_signatures_band1'),
                  table_name='content_signatures',
                  schema='procurement')
    op.drop_table('content_signatures', schema='procurement')
