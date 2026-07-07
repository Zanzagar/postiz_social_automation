"""add auto publish workflow fields

Revision ID: bc1dc7f9ebdb
Revises: e5f6a7b8c9d0
Create Date: 2026-07-06 22:29:39.236867

Adds Phase 1 auto-publish workflow columns to content_rows:
- require_review: a flagged row never auto-releases
- held_at: a held row never auto-releases until resumed
- alt_text: accessibility text; rows with media but no alt text are
  blocked from scheduling/auto-release (NO-ALT block)

Pillars already have `color`; the contract's `target` (int percent) is
derived from the existing `target_distribution` float at the API layer,
so no pillar columns are added here.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bc1dc7f9ebdb"
down_revision: str | Sequence[str] | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add require_review, held_at, alt_text to content_rows."""
    with op.batch_alter_table("content_rows", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("require_review", sa.Boolean(), nullable=False, server_default=sa.text("0"))
        )
        batch_op.add_column(sa.Column("held_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("alt_text", sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove auto-publish workflow columns from content_rows."""
    with op.batch_alter_table("content_rows", schema=None) as batch_op:
        batch_op.drop_column("alt_text")
        batch_op.drop_column("held_at")
        batch_op.drop_column("require_review")
