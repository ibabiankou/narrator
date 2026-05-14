"""Add metadata.editions and metadata.assets

Revision ID: 357447372841
Revises: 2535322d72f0
Create Date: 2026-05-14 12:22:54.353917

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = '357447372841'
down_revision: Union[str, Sequence[str], None] = '2535322d72f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE SCHEMA metadata")
    op.create_table('assets',
                    sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
                    sa.Column('file_name', sa.String(), nullable=False),
                    sa.Column('key', sa.String(), nullable=False),
                    schema='metadata'
                    )
    op.create_table('editions',
                    sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
                    sa.Column('identifiers', JSONB),
                    sa.Column('title', JSONB, nullable=False),
                    sa.Column('description', sa.String()),
                    sa.Column('language', sa.String()),
                    sa.Column('cover', JSONB),
                    sa.Column('epub', JSONB),
                    schema='metadata'
                    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('editions', schema='metadata')
    op.drop_table('assets', schema='metadata')
    op.execute("DROP SCHEMA metadata")
