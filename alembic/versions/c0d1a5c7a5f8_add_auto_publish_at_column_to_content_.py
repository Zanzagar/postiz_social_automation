"""add auto_publish_at column to content_rows

Revision ID: c0d1a5c7a5f8
Revises: 7c37cb595e50
Create Date: 2026-03-18 21:59:53.372835

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c0d1a5c7a5f8"
down_revision: Union[str, Sequence[str], None] = "7c37cb595e50"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add auto_publish_at column to content_rows."""
    with op.batch_alter_table("content_rows", schema=None) as batch_op:
        batch_op.add_column(sa.Column("auto_publish_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Remove auto_publish_at column from content_rows."""
    with op.batch_alter_table("content_rows", schema=None) as batch_op:
        batch_op.drop_column("auto_publish_at")
