"""Add procurement.metadata_id.type

Revision ID: d98f86021ade
Revises: d22295a789e5
Create Date: 2026-05-12 18:49:12.698824

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd98f86021ade'
down_revision: Union[str, Sequence[str], None] = 'd22295a789e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('metadata_ids', sa.Column('type', sa.String(), nullable=False), schema='procurement')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('metadata_ids', 'type', schema='procurement')
