"""add media metadata columns

Revision ID: e91b3a7d54c2
Revises: fc52b56b06a4
Create Date: 2026-07-15 12:00:00.000000

Pasture Phase 3: adds alt_text, default_caption, and season to media_catalog.
season holds canonical lowercase values: spring | summer | fall | winter | any.
Additive only.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e91b3a7d54c2"
down_revision: str | Sequence[str] | None = "fc52b56b06a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add nullable metadata columns to media_catalog."""
    op.add_column("media_catalog", sa.Column("alt_text", sa.Text(), nullable=True))
    op.add_column("media_catalog", sa.Column("default_caption", sa.Text(), nullable=True))
    op.add_column("media_catalog", sa.Column("season", sa.String(length=20), nullable=True))


def downgrade() -> None:
    """Drop the Phase 3 media metadata columns."""
    op.drop_column("media_catalog", "season")
    op.drop_column("media_catalog", "default_caption")
    op.drop_column("media_catalog", "alt_text")
