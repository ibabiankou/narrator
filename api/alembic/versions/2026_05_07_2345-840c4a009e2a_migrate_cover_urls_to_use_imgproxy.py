"""Migrate cover_urls to use imgproxy

Revision ID: 840c4a009e2a
Revises: 2d8dad9aae9e
Create Date: 2026-05-07 23:45:31.965090

"""
import logging
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '840c4a009e2a'
down_revision: Union[str, Sequence[str], None] = '2d8dad9aae9e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)


def upgrade() -> None:
    """Upgrade data."""
    pass


def downgrade() -> None:
    """Downgrade data."""
    pass
