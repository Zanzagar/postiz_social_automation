"""add model_used to content_iterations

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-03-24 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: str | Sequence[str] | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("content_iterations") as batch_op:
        batch_op.add_column(sa.Column("model_used", sa.String(50), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("content_iterations") as batch_op:
        batch_op.drop_column("model_used")
