"""SQLAlchemy models for the Gita Valley content database."""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class ContentRow(Base):
    __tablename__ = "content_rows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    pillar: Mapped[str | None] = mapped_column(String(50), nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    platforms: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON stored as text
    status: Mapped[str] = mapped_column(String(50), default="draft")
    captions: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON stored as text
    postiz_ids: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON stored as text
    posted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    template_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("templates.id"), nullable=True
    )
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    media_catalog_ids: Mapped[str | None] = mapped_column(Text, nullable=True)  # Phase 3
    audience_segment_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Phase 4
    auto_publish_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sheet_row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sheet_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class ContentIteration(Base):
    __tablename__ = "content_iterations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_row_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("content_rows.id"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    old_caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_caption: Mapped[str] = mapped_column(Text, nullable=False)
    refinement_instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    mode: Mapped[str] = mapped_column(String(20), default="refine")
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    pillar: Mapped[str | None] = mapped_column(String(50), nullable=True)
    platform_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    raw_text_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    variables: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    schedule_pattern: Mapped[str | None] = mapped_column(String(100), nullable=True)
    schedule_time: Mapped[str | None] = mapped_column(String(10), nullable=True)  # "HH:MM" format
    default_segment_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Phase 4
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class Pillar(Base):
    __tablename__ = "pillars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)  # hex color for UI
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


# --- Phase 2: Intelligence Layer ---


class WebPage(Base):
    __tablename__ = "web_pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    site: Mapped[str] = mapped_column(String(50), nullable=False)  # "gitavalley", "iskcon"
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    pillar: Mapped[str | None] = mapped_column(String(50), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_crawled: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class WebKnowledge(Base):
    __tablename__ = "web_knowledge"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    web_page_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("web_pages.id"), nullable=True
    )
    fact_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "program", "event", "quote", "link", "description"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pillar: Mapped[str | None] = mapped_column(String(50), nullable=True)
    keywords: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class SocialHistory(Base):
    __tablename__ = "social_history"
    __table_args__ = (UniqueConstraint("platform", "external_id", name="uq_social_platform_extid"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)  # "facebook", "instagram"
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    post_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_urls: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    hashtags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    posted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    reach: Mapped[int] = mapped_column(Integer, default=0)
    pillar: Mapped[str | None] = mapped_column(String(50), nullable=True)  # AI-classified
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class AnalyticsCache(Base):
    __tablename__ = "analytics_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_row_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("content_rows.id"), nullable=True
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    postiz_post_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    reach: Mapped[int] = mapped_column(Integer, default=0)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class HashtagPerformance(Base):
    __tablename__ = "hashtag_performance"
    __table_args__ = (UniqueConstraint("hashtag", "platform", name="uq_hashtag_platform"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hashtag: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    times_used: Mapped[int] = mapped_column(Integer, default=0)
    total_engagement: Mapped[int] = mapped_column(Integer, default=0)
    avg_engagement: Mapped[float] = mapped_column(Float, default=0.0)
    trend: Mapped[str] = mapped_column(String(20), default="stable")  # "up", "down", "stable"
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


# --- Phase 1: Core ---


class PublishConfig(Base):
    __tablename__ = "publish_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    delay_hours: Mapped[int] = mapped_column(Integer, default=2)
    pillar_overrides: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    updated_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


# --- Phase 3: Media & Planning ---


class MediaCatalog(Base):
    __tablename__ = "media_catalog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    original_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    local_path: Mapped[str] = mapped_column(Text, nullable=False)
    postiz_media_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    thumbnail_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    topic: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pillar: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # upload/drive/social_import
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_engagement: Mapped[float] = mapped_column(Float, default=0.0)
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class MediaTag(Base):
    __tablename__ = "media_tags"
    __table_args__ = (UniqueConstraint("media_id", "tag", name="uq_media_tag"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    media_id: Mapped[int] = mapped_column(Integer, ForeignKey("media_catalog.id"), nullable=False)
    tag: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # ai/manual


class MediaPerformance(Base):
    __tablename__ = "media_performance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    media_id: Mapped[int] = mapped_column(Integer, ForeignKey("media_catalog.id"), nullable=False)
    content_row_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("content_rows.id"), nullable=True
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    engagement_score: Mapped[float] = mapped_column(Float, default=0.0)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class MediaAdapted(Base):
    __tablename__ = "media_adapted"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    media_id: Mapped[int] = mapped_column(Integer, ForeignKey("media_catalog.id"), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    format: Mapped[str] = mapped_column(String(20), nullable=False)  # post/story/carousel
    adapted_path: Mapped[str] = mapped_column(Text, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    has_text_overlay: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
