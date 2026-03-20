"""add target_distribution to pillars

Revision ID: bdc07ce948af
Revises: 96b6224398c8
Create Date: 2026-03-20 00:58:12.911198

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "bdc07ce948af"
down_revision: Union[str, Sequence[str], None] = "96b6224398c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create pillars table if missing, then add target_distribution column."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "pillars" not in inspector.get_table_names():
        op.create_table(
            "pillars",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("color", sa.String(length=20), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("target_distribution", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )
    else:
        with op.batch_alter_table("pillars", schema=None) as batch_op:
            batch_op.add_column(sa.Column("target_distribution", sa.Float(), nullable=True))


def downgrade() -> None:
    """Drop pillars table (created in this migration for the first time in the chain)."""
    op.drop_table("pillars")
