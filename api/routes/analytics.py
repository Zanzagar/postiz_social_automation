"""Analytics API endpoints.

Legacy endpoints (shapes unchanged): /overview, /pillars, /top-posts.
V2 endpoints (unified content_rows+analytics_cache UNION social_history
data set): /summary, /posts, /pillar-insights, /platforms, /rhythm,
/sync, /hashtags. See content_engine.analytics.unified for the data
model and documented conventions.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from api.auth import get_current_user

router = APIRouter(
    prefix="/api/analytics", tags=["analytics"], dependencies=[Depends(get_current_user)]
)

_DEFAULT_DB_PATH = str(Path("data/gvsa.db"))

RangeParam = Literal["7d", "30d", "90d", "365d", "all"]


def get_db_path() -> str:
    """Return path to SQLite database. Patchable for tests."""
    return _DEFAULT_DB_PATH


def get_now() -> datetime | None:
    """Clock dependency — overridden in tests to freeze time.

    None means "use real UTC now" (resolved inside the query layer).
    """
    return None


# ---------------------------------------------------------------------------
# Response models (defined here — api/schemas.py is owned elsewhere)
# ---------------------------------------------------------------------------


class KPI(BaseModel):
    value: float | None  # None = incomputable (e.g. avg_rate with no reach data)
    delta_pct: float | None = None
    series: list[float]


class SummaryKPIs(BaseModel):
    posts: KPI
    engagement: KPI
    avg_rate: KPI
    reach: KPI


class DayValue(BaseModel):
    date: str
    value: int


class EngagementByDay(BaseModel):
    current: list[DayValue]
    previous: list[DayValue]


class TopPost(BaseModel):
    id: int | None = None
    source: Literal["app", "history"]
    title: str
    platform: str
    date: str
    pillar: str | None = None
    likes: int
    comments: int
    engagement: int
    rate: float | None = None


class Insight(BaseModel):
    tone: Literal["sage", "terra"]
    title: str
    body: str


class SourceCounts(BaseModel):
    app: int
    history: int


class SummaryResponse(BaseModel):
    range: str
    kpis: SummaryKPIs
    engagement_by_day: EngagementByDay
    top_post: TopPost | None = None
    insights: list[Insight]
    sources: SourceCounts


class PostItem(BaseModel):
    id: int | None = None
    source: Literal["app", "history"]
    title: str
    pillar: str | None = None
    platforms: list[str]
    date: str
    engagement: int
    rate: float | None = None
    trend: Literal["up", "down", "flat"]


class PostsResponse(BaseModel):
    posts: list[PostItem]
    total: int


class PillarStats(BaseModel):
    pillar: str
    color: str | None = None
    posts: int
    engagement: int
    rate: float | None = None
    target_pct: float | None = None
    actual_pct: float
    weekly_series: list[int]


class PillarInsightsResponse(BaseModel):
    pillars: list[PillarStats]
    insights: list[Insight]


class PlatformStats(BaseModel):
    platform: str
    posts: int
    engagement: int
    reach: int
    rate: float | None = None


class HeatmapPeak(BaseModel):
    day: int
    bucket: int


class Heatmap(BaseModel):
    days: list[list[float]]
    hour_buckets: list[str]
    peak: HeatmapPeak | None = None
    sample_size: int


class PlatformsResponse(BaseModel):
    platforms: list[PlatformStats]
    heatmap: Heatmap


class WeekEntry(BaseModel):
    label: str
    posted: int
    target: int | None = None


class FestivalEntry(BaseModel):
    date: str
    name: str
    posts: int
    lift_pct: float | None = None
    pending: bool


class Consistency(BaseModel):
    on_target_weeks: int | None = None
    total_weeks: int


class BestSlot(BaseModel):
    day: str
    hour_bucket: str


class Season(BaseModel):
    total_posts: int
    consistency: Consistency
    best_slot: BestSlot | None = None
    avg_lead_days: float | None = None


class RhythmResponse(BaseModel):
    weeks: list[WeekEntry]
    festivals: list[FestivalEntry]
    season: Season


class SyncResponse(BaseModel):
    synced: int
    failed: int
    skipped: int
    rate_limited: bool


class HashtagItem(BaseModel):
    hashtag: str
    avg_engagement: float
    times_used: int
    trend: str


class HashtagsResponse(BaseModel):
    hashtags: list[HashtagItem]
    source: Literal["performance", "history"]


# ---------------------------------------------------------------------------
# Legacy endpoints — response shapes MUST NOT change
# ---------------------------------------------------------------------------


@router.get("/overview")
async def get_overview(db_path: str = Depends(get_db_path)):
    """Return aggregate engagement overview."""
    from content_engine.analytics.correlation import AnalyticsEngine

    engine = AnalyticsEngine(db_path)
    return engine.get_overview()


@router.get("/pillars")
async def get_pillar_breakdown(db_path: str = Depends(get_db_path)):
    """Return engagement stats grouped by content pillar."""
    from content_engine.analytics.correlation import AnalyticsEngine

    engine = AnalyticsEngine(db_path)
    return {"pillars": engine.get_pillar_breakdown()}


@router.get("/top-posts")
async def get_top_posts(
    limit: int = Query(default=10, le=50),
    db_path: str = Depends(get_db_path),
):
    """Return top posts by engagement."""
    from content_engine.analytics.correlation import AnalyticsEngine

    engine = AnalyticsEngine(db_path)
    return {"posts": engine.get_top_posts(limit=limit)}


# ---------------------------------------------------------------------------
# V2 endpoints — unified performance set
# ---------------------------------------------------------------------------


@router.get("/summary", response_model=SummaryResponse)
async def get_summary(
    range: RangeParam = Query(default="30d"),
    db_path: str = Depends(get_db_path),
    now: datetime | None = Depends(get_now),
):
    """KPIs, engagement-by-day, top post, and rule-based insights."""
    from content_engine.analytics import unified

    return unified.get_summary(db_path, range_key=range, now=now)


@router.get("/posts", response_model=PostsResponse)
async def get_posts(
    range: RangeParam = Query(default="30d"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db_path: str = Depends(get_db_path),
    now: datetime | None = Depends(get_now),
):
    """Unified posts sorted by engagement, paginated."""
    from content_engine.analytics import unified

    return unified.get_posts(db_path, range_key=range, limit=limit, offset=offset, now=now)


@router.get("/pillar-insights", response_model=PillarInsightsResponse)
async def get_pillar_insights(
    range: RangeParam = Query(default="30d"),
    db_path: str = Depends(get_db_path),
    now: datetime | None = Depends(get_now),
):
    """Per-pillar performance vs target distribution, with insights."""
    from content_engine.analytics import unified

    return unified.get_pillar_insights(db_path, range_key=range, now=now)


@router.get("/platforms", response_model=PlatformsResponse)
async def get_platforms(
    range: RangeParam = Query(default="30d"),
    db_path: str = Depends(get_db_path),
    now: datetime | None = Depends(get_now),
):
    """Per-platform performance and posting-time heatmap."""
    from content_engine.analytics import unified

    return unified.get_platforms(db_path, range_key=range, now=now)


@router.get("/rhythm", response_model=RhythmResponse)
async def get_rhythm(
    range: RangeParam = Query(default="30d"),
    db_path: str = Depends(get_db_path),
    now: datetime | None = Depends(get_now),
):
    """Weekly posting rhythm, festival markers, and season summary."""
    from content_engine.analytics import unified

    return unified.get_rhythm(db_path, range_key=range, now=now)


@router.post("/sync", response_model=SyncResponse)
async def sync_analytics(db_path: str = Depends(get_db_path)):
    """Run the converged Postiz analytics sync + hashtag refresh.

    Rate-limit aware (30 req/h shared budget) and safe with 0 eligible
    rows — no Postiz client is constructed unless rows need syncing.
    """
    from api.dependencies import get_settings
    from content_engine.analytics.postiz_sync import sync_all
    from content_engine.postiz import PostizClient

    settings = get_settings()
    client = None
    if settings.postiz_api_key:
        client = PostizClient(
            api_key=settings.postiz_api_key,
            base_url=settings.postiz_base_url,
        )
    # sync_all does blocking HTTP + time.sleep backoff — run it off the
    # event loop so a long sync can't freeze every other request.
    return await asyncio.to_thread(sync_all, db_path, client=client)


@router.get("/hashtags", response_model=HashtagsResponse)
async def get_hashtags(
    platform: str | None = Query(default=None),
    count: int = Query(default=8, ge=1, le=50),
    db_path: str = Depends(get_db_path),
):
    """Top hashtags by avg engagement, lazily populated from history."""
    from content_engine.analytics import unified

    return unified.get_hashtags(db_path, platform=platform, count=count)
