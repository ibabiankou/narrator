"""Create procurement schema

Revision ID: 7ae176a85410
Revises: 840c4a009e2a
Create Date: 2026-05-11 19:11:34.648686

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7ae176a85410'
down_revision: Union[str, Sequence[str], None] = '840c4a009e2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE SCHEMA procurement")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP SCHEMA procurement")
