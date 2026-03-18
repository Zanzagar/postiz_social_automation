"""SQLAlchemy models for the Gita Valley content database."""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
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
    default_segment_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Phase 4
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


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
