"""add calendar_plans table

Revision ID: 757e503cb80d
Revises: bdc07ce948af
Create Date: 2026-03-20 01:06:32.147166

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "757e503cb80d"
down_revision: Union[str, Sequence[str], None] = "bdc07ce948af"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create calendar_plans table."""
    op.create_table(
        "calendar_plans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("date_range_start", sa.DateTime(), nullable=False),
        sa.Column("date_range_end", sa.DateTime(), nullable=False),
        sa.Column("platforms", sa.Text(), nullable=True),
        sa.Column("plan_data", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Drop calendar_plans table."""
    op.drop_table("calendar_plans")
