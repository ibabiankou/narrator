"""Add sections table

Revision ID: d8df8166266c
Revises: b33959ce8d24
Create Date: 2025-11-17 17:23:07.653739

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8df8166266c'
down_revision: Union[str, Sequence[str], None] = 'b33959ce8d24'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'sections',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('book_id', sa.UUID, sa.ForeignKey('books.id'), nullable=False),

        sa.Column('page_index', sa.Integer, nullable=False),
        sa.Column('section_index', sa.Integer, nullable=False),

        sa.Column('content', sa.String(), nullable=False),
    )
    op.create_index('ik_section_book_page', 'sections', ['book_id', 'page_index'])

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ik_section_book_page', if_exists=True)
    op.drop_table('sections', if_exists=True)
