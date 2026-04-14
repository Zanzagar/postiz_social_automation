"""add few_shot_examples table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-24 14:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "few_shot_examples",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("pillar", sa.String(50), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("caption", sa.Text(), nullable=False),
        sa.Column("engagement_score", sa.Float(), server_default="0.0"),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("1"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("few_shot_examples")
