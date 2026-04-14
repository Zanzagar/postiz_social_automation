"""add preference_pairs table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-24 16:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "preference_pairs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("edited_text", sa.Text(), nullable=False),
        sa.Column("instruction", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("preference_pairs")
