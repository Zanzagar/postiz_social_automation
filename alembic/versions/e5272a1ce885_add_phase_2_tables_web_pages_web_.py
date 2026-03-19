"""add Phase 2 tables: web_pages, web_knowledge, social_history, analytics_cache, hashtag_performance

Revision ID: e5272a1ce885
Revises: c0d1a5c7a5f8
Create Date: 2026-03-18 22:04:13.413043

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e5272a1ce885"
down_revision: Union[str, Sequence[str], None] = "c0d1a5c7a5f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Phase 2 intelligence tables."""
    op.create_table(
        "web_pages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("site", sa.String(length=50), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("pillar", sa.String(length=50), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("last_crawled", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "web_knowledge",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("web_page_id", sa.Integer(), nullable=True),
        sa.Column("fact_type", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("pillar", sa.String(length=50), nullable=True),
        sa.Column("keywords", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["web_page_id"], ["web_pages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "social_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("post_text", sa.Text(), nullable=True),
        sa.Column("media_urls", sa.Text(), nullable=True),
        sa.Column("hashtags", sa.Text(), nullable=True),
        sa.Column("posted_at", sa.DateTime(), nullable=True),
        sa.Column("likes", sa.Integer(), nullable=False),
        sa.Column("comments", sa.Integer(), nullable=False),
        sa.Column("shares", sa.Integer(), nullable=False),
        sa.Column("reach", sa.Integer(), nullable=False),
        sa.Column("pillar", sa.String(length=50), nullable=True),
        sa.Column("imported_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("platform", "external_id", name="uq_social_platform_extid"),
    )
    op.create_table(
        "analytics_cache",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("content_row_id", sa.Integer(), nullable=True),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("postiz_post_id", sa.String(length=255), nullable=True),
        sa.Column("likes", sa.Integer(), nullable=False),
        sa.Column("shares", sa.Integer(), nullable=False),
        sa.Column("comments", sa.Integer(), nullable=False),
        sa.Column("reach", sa.Integer(), nullable=False),
        sa.Column("impressions", sa.Integer(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["content_row_id"], ["content_rows.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "hashtag_performance",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("hashtag", sa.String(length=255), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("times_used", sa.Integer(), nullable=False),
        sa.Column("total_engagement", sa.Integer(), nullable=False),
        sa.Column("avg_engagement", sa.Float(), nullable=False),
        sa.Column("trend", sa.String(length=20), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hashtag", "platform", name="uq_hashtag_platform"),
    )


def downgrade() -> None:
    """Drop Phase 2 intelligence tables."""
    op.drop_table("analytics_cache")
    op.drop_table("web_knowledge")
    op.drop_table("web_pages")
    op.drop_table("social_history")
    op.drop_table("hashtag_performance")
