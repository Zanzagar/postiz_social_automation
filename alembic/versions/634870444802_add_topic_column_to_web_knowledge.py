"""Add topic column to web_knowledge

Revision ID: 634870444802
Revises: e5272a1ce885
Create Date: 2026-03-19 02:28:30.951145

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "634870444802"
down_revision: Union[str, Sequence[str], None] = "e5272a1ce885"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add topic column for source-faithful knowledge categorization."""
    with op.batch_alter_table("web_knowledge", schema=None) as batch_op:
        batch_op.add_column(sa.Column("topic", sa.String(100), nullable=True))


def downgrade() -> None:
    """Remove topic column."""
    with op.batch_alter_table("web_knowledge", schema=None) as batch_op:
        batch_op.drop_column("topic")
