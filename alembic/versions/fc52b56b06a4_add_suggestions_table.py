"""add suggestions table

Revision ID: fc52b56b06a4
Revises: bc1dc7f9ebdb
Create Date: 2026-07-14 20:26:09.144145

Adds the suggestions table backing the SQLite-based suggestion system
(festival reminders, pillar gaps, template reminders). Replaces the old
Google Sheets suggestions tab. Additive only.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fc52b56b06a4"
down_revision: str | Sequence[str] | None = "bc1dc7f9ebdb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the suggestions table."""
    op.create_table(
        "suggestions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("pillar", sa.String(length=50), nullable=True),
        sa.Column("suggested_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="suggested"),
        sa.Column("source_key", sa.String(length=255), nullable=False),
        sa.Column("content_row_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_key", name="uq_suggestions_source_key"),
        sa.ForeignKeyConstraint(
            ["content_row_id"], ["content_rows.id"], name="fk_suggestions_content_row_id"
        ),
    )


def downgrade() -> None:
    """Drop the suggestions table."""
    op.drop_table("suggestions")
