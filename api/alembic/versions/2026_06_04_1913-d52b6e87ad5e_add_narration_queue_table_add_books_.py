"""Add narration_queue table; Add books.narration_request

Revision ID: d52b6e87ad5e
Revises: 357447372841
Create Date: 2026-06-04 19:13:00.759395

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = 'd52b6e87ad5e'
down_revision: Union[str, Sequence[str], None] = '357447372841'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('books', sa.Column('narration_request', JSONB, nullable=True))
    op.create_table('narration_queue',
                    sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True, nullable=False),
                    sa.Column('book_id', sa.Uuid(), nullable=False),
                    sa.Column('tts_model', sa.String(), nullable=False),
                    sa.Column('voice', sa.String(), nullable=False),
                    sa.Column('track_base_name', sa.String(), nullable=False),
                    sa.Column('order', sa.Integer(), nullable=False),
                    sa.Column('fragments', JSONB, nullable=False),
                    sa.Column('added', sa.DateTime(), nullable=False),
                    sa.Column('sent', sa.DateTime()),
                    sa.Column('narration_time_s', sa.Float()),
                    sa.Column('completed', sa.DateTime()),
                    sa.Column('duration_s', sa.Float()),
                    sa.Column('size_bytes', sa.Integer()),
                    sa.ForeignKeyConstraint(['book_id'], ['books.id'])
                    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('narration_queue')
    op.drop_column('books', 'narration_request')
