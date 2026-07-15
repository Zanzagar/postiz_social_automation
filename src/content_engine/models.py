"""Pydantic models for content, posts, and configuration."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, HttpUrl


class ContentStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    POSTED = "posted"
    ERROR = "error"


class Platform(StrEnum):
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    TIKTOK = "tiktok"
    THREADS = "threads"
    LINKEDIN = "linkedin"


class ContentRow(BaseModel):
    """A single row from the content Google Sheet."""

    row_number: int
    date: datetime
    content_pillar: str | None = None
    raw_text: str
    media_url: HttpUrl | None = None
    platforms: dict[Platform, bool]
    status: ContentStatus
    captions: dict[Platform, str | None]
    feedback: str | None = None
    postiz_ids: str | None = None
    posted_at: datetime | None = None
    error_msg: str | None = None
    source: str = "staff"


class Suggestion(BaseModel):
    """AI-generated content suggestion for Mode 2 (Suggest)."""

    suggested_date: datetime
    content_idea: str
    suggested_pillar: str
    rationale: str
    media_suggestion: str
    status: str = "suggested"


class PostPerformance(BaseModel):
    """Engagement metrics for a published post.

    Canonical field set per POSTIZ_CONTRACT.md §7 (I2): likes, comments,
    shares, reach, impressions. engagement_rate is computed our side as
    (likes + comments + shares) / reach when reach > 0.
    """

    post_id: str
    platform: Platform
    pillar: str
    posted_at: datetime
    likes: int = 0
    comments: int = 0
    shares: int = 0
    reach: int = 0
    impressions: int = 0
    engagement_rate: float = 0.0


class LearningContext(BaseModel):
    """Accumulated intelligence from post performance analysis."""

    last_updated: datetime
    top_performing_pillars: list[str]
    best_posting_times: dict[str, list[str]]
    hashtag_performance: dict[str, float]
    pillar_distribution: dict[str, float]
    insights: list[str]
