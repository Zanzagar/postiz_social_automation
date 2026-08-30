"""Unified analytics query layer.

One performance data set powering all /api/analytics endpoints:

    (content_rows JOIN analytics_cache ON analytics_cache.content_row_id,
     source="app")
    UNION
    (social_history rows, source="history")

Conventions (documented decisions):
- engagement = likes + comments + shares
- rate = engagement / reach * 100 when reach > 0, else None
- Range windows are calendar-day based: current window covers ``days``
  calendar days ending today (inclusive); the previous window is the
  immediately preceding equal-length day window.
- App posts are dated by COALESCE(content_rows.posted_at, content_rows.date);
  each analytics_cache row is one per-platform record. For post-level
  views, app records are aggregated per content_row (platforms combined,
  metrics summed). History rows are one post each.
- Records without a parseable date are excluded from range-windowed
  results (they cannot be placed in a window).
- All values come from real data; endpoints return well-formed empty
  structures when tables are empty. Nothing is fabricated.
"""

import json
import logging
import math
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

RANGE_DAYS = {"7d": 7, "30d": 30, "90d": 90, "365d": 365}
ALL_RANGE = "all"  # no lower time bound — window starts at the earliest record
DEFAULT_RANGE = "30d"
MAX_SERIES_BUCKETS = 14

HOUR_BUCKET_LABELS = ["6a", "9a", "12p", "3p", "6p", "9p"]
_HOUR_BUCKET_CENTERS = [6, 9, 12, 15, 18, 21]

# Heatmap/rhythm buckets are shown as wall-clock times in the UI ("Best
# time to post: 6p"), so bucketing converts stored UTC datetimes to a
# display timezone first. Windowing and stored values stay UTC.
DEFAULT_DISPLAY_TZ = "America/New_York"


def _display_tz() -> ZoneInfo:
    """Display timezone for hour/weekday bucketing (env-overridable)."""
    return ZoneInfo(os.environ.get("GV_DISPLAY_TZ", DEFAULT_DISPLAY_TZ))


DAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

_DEFAULT_CALENDAR_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent / "data" / "iskcon_calendar.json"
)

# Minimum posts in a window before rule-based insights are emitted.
MIN_POSTS_FOR_INSIGHTS = 5


def utcnow() -> datetime:
    """Naive-UTC now. Injectable in every public function for testing."""
    return datetime.now(UTC).replace(tzinfo=None)


def parse_dt(value: object) -> datetime | None:
    """Parse SQLite datetime text to naive UTC. None when unparseable.

    Handles both content_rows format ('2026-03-18 23:01:58.572527') and
    social_history format ('2022-05-25T17:12:15+0000').
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        s = str(value).strip()
        if not s:
            return None
        if s.endswith("+0000"):
            s = s[:-5] + "+00:00"
        s = s.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC).replace(tzinfo=None)
    return dt


@dataclass
class PlatformRecord:
    """One per-platform performance record (app or history)."""

    id: int | None
    source: str  # "app" | "history"
    text: str
    pillar: str | None
    platform: str
    date: datetime | None
    likes: int
    comments: int
    shares: int
    reach: int
    created_at: datetime | None = None  # app posts only

    @property
    def engagement(self) -> int:
        return self.likes + self.comments + self.shares

    @property
    def rate(self) -> float | None:
        if self.reach > 0:
            return self.engagement / self.reach * 100
        return None


@dataclass
class UnifiedPost:
    """A post-level view: app records aggregated per content_row."""

    id: int | None
    source: str
    text: str
    pillar: str | None
    platforms: list[str] = field(default_factory=list)
    date: datetime | None = None
    likes: int = 0
    comments: int = 0
    shares: int = 0
    reach: int = 0
    created_at: datetime | None = None
    top_platform: str = ""

    @property
    def engagement(self) -> int:
        return self.likes + self.comments + self.shares

    @property
    def rate(self) -> float | None:
        if self.reach > 0:
            return self.engagement / self.reach * 100
        return None


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def fetch_platform_records(db_path: str) -> list[PlatformRecord]:
    """Load all unified per-platform records from the database."""
    conn = _connect(db_path)
    records: list[PlatformRecord] = []

    if _table_exists(conn, "analytics_cache") and _table_exists(conn, "content_rows"):
        rows = conn.execute(
            """
            SELECT ac.content_row_id AS id, cr.raw_text AS text, cr.pillar AS pillar,
                   ac.platform AS platform,
                   COALESCE(cr.posted_at, cr.date) AS date,
                   ac.likes, ac.comments, ac.shares, ac.reach,
                   cr.created_at AS created_at
            FROM analytics_cache ac
            JOIN content_rows cr ON ac.content_row_id = cr.id
            """
        ).fetchall()
        for r in rows:
            records.append(
                PlatformRecord(
                    id=r["id"],
                    source="app",
                    text=r["text"] or "",
                    pillar=r["pillar"],
                    platform=r["platform"] or "",
                    date=parse_dt(r["date"]),
                    likes=r["likes"] or 0,
                    comments=r["comments"] or 0,
                    shares=r["shares"] or 0,
                    reach=r["reach"] or 0,
                    created_at=parse_dt(r["created_at"]),
                )
            )

    if _table_exists(conn, "social_history"):
        rows = conn.execute(
            """
            SELECT id, post_text AS text, pillar, platform, posted_at AS date,
                   likes, comments, shares, reach
            FROM social_history
            """
        ).fetchall()
        for r in rows:
            records.append(
                PlatformRecord(
                    id=r["id"],
                    source="history",
                    text=r["text"] or "",
                    pillar=r["pillar"],
                    platform=r["platform"] or "",
                    date=parse_dt(r["date"]),
                    likes=r["likes"] or 0,
                    comments=r["comments"] or 0,
                    shares=r["shares"] or 0,
                    reach=r["reach"] or 0,
                )
            )

    conn.close()
    return records


def aggregate_posts(records: list[PlatformRecord]) -> list[UnifiedPost]:
    """Aggregate per-platform records into post-level entries.

    App records with the same content_row id merge into one post
    (platforms combined, metrics summed). History records are 1:1.
    """
    app_posts: dict[int | None, UnifiedPost] = {}
    posts: list[UnifiedPost] = []

    for rec in records:
        if rec.source == "app":
            post = app_posts.get(rec.id)
            if post is None:
                post = UnifiedPost(
                    id=rec.id,
                    source="app",
                    text=rec.text,
                    pillar=rec.pillar,
                    date=rec.date,
                    created_at=rec.created_at,
                )
                app_posts[rec.id] = post
                posts.append(post)
            if rec.platform and rec.platform not in post.platforms:
                post.platforms.append(rec.platform)
            post.likes += rec.likes
            post.comments += rec.comments
            post.shares += rec.shares
            post.reach += rec.reach
        else:
            posts.append(
                UnifiedPost(
                    id=rec.id,
                    source="history",
                    text=rec.text,
                    pillar=rec.pillar,
                    platforms=[rec.platform] if rec.platform else [],
                    date=rec.date,
                    likes=rec.likes,
                    comments=rec.comments,
                    shares=rec.shares,
                    reach=rec.reach,
                    top_platform=rec.platform or "",
                )
            )

    # Resolve top_platform for app posts (highest-engagement platform record).
    best: dict[int | None, tuple[int, str]] = {}
    for rec in records:
        if rec.source != "app":
            continue
        current = best.get(rec.id)
        if current is None or rec.engagement > current[0]:
            best[rec.id] = (rec.engagement, rec.platform)
    for post_id, (_, platform) in best.items():
        if post_id in app_posts:
            app_posts[post_id].top_platform = platform

    return posts


# ---------------------------------------------------------------------------
# Window helpers
# ---------------------------------------------------------------------------


def resolve_range(range_key: str | None) -> int:
    """Map a range query param to its day count (default 30d)."""
    return RANGE_DAYS.get(range_key or DEFAULT_RANGE, RANGE_DAYS[DEFAULT_RANGE])


def resolve_days(range_key: str | None, records: list[PlatformRecord], now: datetime) -> int:
    """Day count for a range key, given the loaded records.

    "all" has no lower time bound: the window spans from the earliest
    dated record through today, inclusive (default range when no record
    has a parseable date). Fixed keys pass through to resolve_range.
    """
    if range_key == ALL_RANGE:
        dated = [r.date for r in records if r.date is not None]
        if not dated:
            return RANGE_DAYS[DEFAULT_RANGE]
        return max((now.date() - min(dated).date()).days + 1, 1)
    return resolve_range(range_key)


def window_dates(now: datetime, days: int) -> tuple[date, date]:
    """Return (start_date, end_date) of the current window, inclusive."""
    end = now.date()
    start = end - timedelta(days=days - 1)
    return start, end


def previous_window_dates(now: datetime, days: int) -> tuple[date, date]:
    """Return (start_date, end_date) of the preceding equal-length window."""
    start, _ = window_dates(now, days)
    return start - timedelta(days=days), start - timedelta(days=1)


def in_date_window(d: datetime | None, start: date, end: date) -> bool:
    return d is not None and start <= d.date() <= end


def posts_in_window(posts: list[UnifiedPost], start: date, end: date) -> list[UnifiedPost]:
    return [p for p in posts if in_date_window(p.date, start, end)]


def records_in_window(
    records: list[PlatformRecord], start: date, end: date
) -> list[PlatformRecord]:
    return [r for r in records if in_date_window(r.date, start, end)]


# ---------------------------------------------------------------------------
# Series / KPI helpers
# ---------------------------------------------------------------------------


def _daily_values(posts: list[UnifiedPost], start: date, days: int, metric: str) -> list[float]:
    """Per-day metric values over the window, oldest first, zero-filled."""
    values = [0.0] * days
    for p in posts:
        if p.date is None:
            continue
        idx = (p.date.date() - start).days
        if 0 <= idx < days:
            if metric == "posts":
                values[idx] += 1
            elif metric == "engagement":
                values[idx] += p.engagement
            elif metric == "reach":
                values[idx] += p.reach
    return values


def _downsample_sum(daily: list[float], max_buckets: int = MAX_SERIES_BUCKETS) -> list[float]:
    """Sum daily values into <= max_buckets buckets, oldest first."""
    n = len(daily)
    if n <= max_buckets:
        return [round(v, 2) for v in daily]
    size = math.ceil(n / max_buckets)
    return [round(sum(daily[i : i + size]), 2) for i in range(0, n, size)]


def _rate_series(
    posts: list[UnifiedPost], start: date, days: int, max_buckets: int = MAX_SERIES_BUCKETS
) -> list[float]:
    """Per-bucket mean rate (only posts with reach>0), 0.0 for empty buckets."""
    size = math.ceil(days / max_buckets) if days > max_buckets else 1
    n_buckets = math.ceil(days / size)
    sums = [0.0] * n_buckets
    counts = [0] * n_buckets
    for p in posts:
        if p.date is None or p.rate is None:
            continue
        idx = (p.date.date() - start).days
        if 0 <= idx < days:
            b = idx // size
            sums[b] += p.rate
            counts[b] += 1
    return [round(sums[i] / counts[i], 2) if counts[i] else 0.0 for i in range(n_buckets)]


def _delta_pct(current: float, previous: float) -> float | None:
    """Percent change vs previous window; None when previous is 0/absent."""
    if previous > 0:
        return round((current - previous) / previous * 100, 1)
    return None


def _mean_rate(posts: list[UnifiedPost]) -> float | None:
    """Mean of per-post rates; None when no post has a computable rate."""
    rates = [p.rate for p in posts if p.rate is not None]
    if not rates:
        return None
    return sum(rates) / len(rates)


def _title_of(text: str, max_len: int = 80) -> str:
    """First ~max_len chars of the post text as a single line."""
    single = " ".join((text or "").split())
    if len(single) <= max_len:
        return single
    return single[:max_len].rstrip() + "…"


# ---------------------------------------------------------------------------
# Insight rules (deterministic, real data only)
# ---------------------------------------------------------------------------


def compute_summary_insights(posts: list[UnifiedPost], records: list[PlatformRecord]) -> list[dict]:
    """Rule-based summary insights. Max 2. Empty when < 5 posts.

    - sage: best pillar's avg engagement >= 1.5x the overall average.
    - terra: a platform with avg rate < half the overall avg rate across
      >= 3 rated posts.
    """
    if len(posts) < MIN_POSTS_FOR_INSIGHTS:
        return []

    insights: list[dict] = []
    overall_avg = sum(p.engagement for p in posts) / len(posts)

    # Rule 1 (sage): standout pillar.
    if overall_avg > 0:
        pillar_groups: dict[str, list[UnifiedPost]] = {}
        for p in posts:
            if p.pillar:
                pillar_groups.setdefault(p.pillar, []).append(p)
        best_pillar = None
        best_avg = 0.0
        for pillar, group in pillar_groups.items():
            avg = sum(p.engagement for p in group) / len(group)
            if avg > best_avg:
                best_avg = avg
                best_pillar = pillar
        if best_pillar is not None and best_avg >= 1.5 * overall_avg:
            insights.append(
                {
                    "tone": "sage",
                    "title": f"{best_pillar} is your standout pillar",
                    "body": (
                        f"{best_pillar} posts average {best_avg:.0f} engagement — "
                        f"{best_avg / overall_avg:.1f}x your overall average of "
                        f"{overall_avg:.0f}."
                    ),
                }
            )

    # Rule 2 (terra): underperforming platform by rate.
    rated = [r for r in records if r.rate is not None]
    if rated:
        overall_rate = sum(r.rate for r in rated) / len(rated)
        platform_groups: dict[str, list[PlatformRecord]] = {}
        for r in rated:
            if r.platform:
                platform_groups.setdefault(r.platform, []).append(r)
        worst = None
        worst_rate = None
        for platform, group in sorted(platform_groups.items()):
            if len(group) < 3:
                continue
            avg_rate = sum(g.rate for g in group) / len(group)
            if avg_rate < 0.5 * overall_rate and (worst_rate is None or avg_rate < worst_rate):
                worst = platform
                worst_rate = avg_rate
        if worst is not None:
            insights.append(
                {
                    "tone": "terra",
                    "title": f"{worst.capitalize()} engagement rate is lagging",
                    "body": (
                        f"{worst.capitalize()} posts average a {worst_rate:.1f}% engagement "
                        f"rate — less than half your overall average of "
                        f"{overall_rate:.1f}%."
                    ),
                }
            )

    return insights[:2]


def compute_pillar_insights(pillar_stats: list[dict]) -> list[dict]:
    """Rule-based pillar insights. Max 2.

    - terra 'over-indexed': among pillars > 5pp over target, the one with
      the lowest rate.
    - sage 'underused but works': among pillars under target with an
      above-average rate, the one with the largest gap.
    """
    insights: list[dict] = []

    # terra: over-indexed with lowest rate.
    over = [
        s
        for s in pillar_stats
        if s["target_pct"] is not None
        and s["actual_pct"] - s["target_pct"] > 5
        and s["rate"] is not None
    ]
    if over:
        worst = min(over, key=lambda s: s["rate"])
        insights.append(
            {
                "tone": "terra",
                "title": f"{worst['pillar']} may be over-indexed",
                "body": (
                    f"{worst['pillar']} is {worst['actual_pct'] - worst['target_pct']:.0f}pp "
                    f"over its target share while posting the lowest engagement rate "
                    f"({worst['rate']:.1f}%)."
                ),
            }
        )

    # sage: under target but above-average rate.
    rated = [s for s in pillar_stats if s["rate"] is not None]
    if rated:
        avg_rate = sum(s["rate"] for s in rated) / len(rated)
        under = [
            s
            for s in rated
            if s["target_pct"] is not None
            and s["actual_pct"] < s["target_pct"]
            and s["rate"] > avg_rate
        ]
        if under:
            best = max(under, key=lambda s: s["target_pct"] - s["actual_pct"])
            insights.append(
                {
                    "tone": "sage",
                    "title": f"{best['pillar']} is underused but works",
                    "body": (
                        f"{best['pillar']} runs {best['target_pct'] - best['actual_pct']:.0f}pp "
                        f"under its target share yet beats your average engagement rate "
                        f"({best['rate']:.1f}% vs {avg_rate:.1f}%)."
                    ),
                }
            )

    return insights[:2]


# ---------------------------------------------------------------------------
# Heatmap
# ---------------------------------------------------------------------------


def hour_bucket(hour: int) -> int:
    """Map an hour (0-23) to the nearest of 6 buckets (centers 6..21)."""
    return min(
        range(len(_HOUR_BUCKET_CENTERS)),
        key=lambda i: abs(hour - _HOUR_BUCKET_CENTERS[i]),
    )


def compute_heatmap(records: list[PlatformRecord]) -> dict:
    """Posting heatmap: normalized avg engagement per (weekday, hour bucket).

    Intensity is each cell's average engagement divided by the max cell
    average (0..1). Cells with no posts are 0.0. All-empty data yields
    all zeros and a null peak.

    Weekday and hour are taken in the display timezone (GV_DISPLAY_TZ,
    default America/New_York) — the UI labels buckets as local wall-clock
    times. Stored datetimes remain naive UTC.
    """
    sums = [[0.0] * len(HOUR_BUCKET_LABELS) for _ in range(7)]
    counts = [[0] * len(HOUR_BUCKET_LABELS) for _ in range(7)]
    sample_size = 0
    tz = _display_tz()

    for r in records:
        if r.date is None:
            continue
        local = r.date.replace(tzinfo=UTC).astimezone(tz)
        day = local.weekday()  # Mon=0..Sun=6, display-timezone wall clock
        bucket = hour_bucket(local.hour)
        sums[day][bucket] += r.engagement
        counts[day][bucket] += 1
        sample_size += 1

    averages = [
        [sums[d][b] / counts[d][b] if counts[d][b] else 0.0 for b in range(6)] for d in range(7)
    ]
    max_avg = max((averages[d][b] for d in range(7) for b in range(6)), default=0.0)

    days = [
        [round(averages[d][b] / max_avg, 3) if max_avg > 0 else 0.0 for b in range(6)]
        for d in range(7)
    ]

    peak = None
    if sample_size > 0 and max_avg > 0:
        for d in range(7):
            for b in range(6):
                if averages[d][b] == max_avg:
                    peak = {"day": d, "bucket": b}
                    break
            if peak:
                break

    return {
        "days": days,
        "hour_buckets": list(HOUR_BUCKET_LABELS),
        "peak": peak,
        "sample_size": sample_size,
    }


# ---------------------------------------------------------------------------
# Endpoint-level queries
# ---------------------------------------------------------------------------


def get_summary(db_path: str, range_key: str = DEFAULT_RANGE, now: datetime | None = None) -> dict:
    """GET /api/analytics/summary payload."""
    now = now or utcnow()
    records = fetch_platform_records(db_path)
    posts = aggregate_posts(records)
    days = resolve_days(range_key, records, now)
    start, end = window_dates(now, days)
    is_all = range_key == ALL_RANGE

    current = posts_in_window(posts, start, end)
    if is_all:
        # "all" spans everything — there is no previous window to compare
        # against, so deltas stay None and the previous series is empty.
        prev_start = start
        previous: list[UnifiedPost] = []
    else:
        prev_start, prev_end = previous_window_dates(now, days)
        previous = posts_in_window(posts, prev_start, prev_end)
    current_records = records_in_window(records, start, end)

    cur_engagement = sum(p.engagement for p in current)
    prev_engagement = sum(p.engagement for p in previous)
    cur_reach = sum(p.reach for p in current)
    prev_reach = sum(p.reach for p in previous)
    cur_rate = _mean_rate(current)
    prev_rate = _mean_rate(previous)

    kpis = {
        "posts": {
            "value": len(current),
            "delta_pct": _delta_pct(len(current), len(previous)),
            "series": _downsample_sum(_daily_values(current, start, days, "posts")),
        },
        "engagement": {
            "value": cur_engagement,
            "delta_pct": _delta_pct(cur_engagement, prev_engagement),
            "series": _downsample_sum(_daily_values(current, start, days, "engagement")),
        },
        "avg_rate": {
            "value": round(cur_rate, 2) if cur_rate is not None else None,
            "delta_pct": _delta_pct(cur_rate, prev_rate)
            if cur_rate is not None and prev_rate is not None
            else None,
            "series": _rate_series(current, start, days),
        },
        "reach": {
            "value": cur_reach,
            "delta_pct": _delta_pct(cur_reach, prev_reach),
            "series": _downsample_sum(_daily_values(current, start, days, "reach")),
        },
    }

    cur_daily = _daily_values(current, start, days, "engagement")
    prev_daily = _daily_values(previous, prev_start, days, "engagement")
    engagement_by_day = {
        "current": [
            {"date": (start + timedelta(days=i)).isoformat(), "value": int(cur_daily[i])}
            for i in range(days)
        ],
        "previous": []
        if is_all
        else [
            {"date": (prev_start + timedelta(days=i)).isoformat(), "value": int(prev_daily[i])}
            for i in range(days)
        ],
    }

    top_post = None
    if current:
        best = max(current, key=lambda p: p.engagement)
        top_post = {
            "id": best.id,
            "source": best.source,
            "title": _title_of(best.text),
            "platform": best.top_platform,
            "date": best.date.date().isoformat() if best.date else "",
            "pillar": best.pillar,
            "likes": best.likes,
            "comments": best.comments,
            "engagement": best.engagement,
            "rate": round(best.rate, 2) if best.rate is not None else None,
        }

    sources = {
        "app": sum(1 for p in current if p.source == "app"),
        "history": sum(1 for p in current if p.source == "history"),
    }

    return {
        "range": range_key,
        "kpis": kpis,
        "engagement_by_day": engagement_by_day,
        "top_post": top_post,
        "insights": compute_summary_insights(current, current_records),
        "sources": sources,
    }


def get_posts(
    db_path: str,
    range_key: str = DEFAULT_RANGE,
    limit: int = 20,
    offset: int = 0,
    now: datetime | None = None,
) -> dict:
    """GET /api/analytics/posts payload (sorted by engagement desc)."""
    now = now or utcnow()
    records = fetch_platform_records(db_path)
    days = resolve_days(range_key, records, now)
    start, end = window_dates(now, days)

    posts = aggregate_posts(records)
    current = posts_in_window(posts, start, end)
    current.sort(key=lambda p: p.engagement, reverse=True)

    mean_engagement = sum(p.engagement for p in current) / len(current) if current else 0.0

    def trend_of(p: UnifiedPost) -> str:
        if mean_engagement <= 0:
            return "flat"
        ratio = p.engagement / mean_engagement
        if ratio > 1.2:
            return "up"
        if ratio < 0.8:
            return "down"
        return "flat"

    page = current[offset : offset + limit]
    return {
        "posts": [
            {
                "id": p.id,
                "source": p.source,
                "title": _title_of(p.text),
                "pillar": p.pillar,
                "platforms": list(p.platforms),
                "date": p.date.date().isoformat() if p.date else "",
                "engagement": p.engagement,
                "rate": round(p.rate, 2) if p.rate is not None else None,
                "trend": trend_of(p),
            }
            for p in page
        ],
        "total": len(current),
    }


def _load_pillar_meta(db_path: str) -> dict[str, dict]:
    """Pillar name -> {color, target_distribution} from the pillars table."""
    conn = _connect(db_path)
    meta: dict[str, dict] = {}
    if _table_exists(conn, "pillars"):
        try:
            for r in conn.execute("SELECT name, color, target_distribution FROM pillars"):
                meta[r["name"]] = {
                    "color": r["color"],
                    "target_distribution": r["target_distribution"],
                }
        except sqlite3.OperationalError:
            logger.warning("pillars table missing expected columns")
    conn.close()
    return meta


def get_pillar_insights(
    db_path: str, range_key: str = DEFAULT_RANGE, now: datetime | None = None
) -> dict:
    """GET /api/analytics/pillar-insights payload."""
    now = now or utcnow()
    records = fetch_platform_records(db_path)
    days = resolve_days(range_key, records, now)
    start, end = window_dates(now, days)

    posts = aggregate_posts(records)
    current = posts_in_window(posts, start, end)
    total_posts = len(current)
    meta = _load_pillar_meta(db_path)

    groups: dict[str, list[UnifiedPost]] = {}
    for p in current:
        if p.pillar:
            groups.setdefault(p.pillar, []).append(p)

    # Weekly series: posts-per-week over the 12 weeks ending today
    # (7-day blocks back from the window end), oldest first.
    week_starts = [end - timedelta(days=7 * (12 - i) - 1) for i in range(12)]

    pillar_stats: list[dict] = []
    for pillar, group in sorted(groups.items(), key=lambda kv: -sum(p.engagement for p in kv[1])):
        engagement = sum(p.engagement for p in group)
        reach = sum(p.reach for p in group)
        rate = engagement / reach * 100 if reach > 0 else None
        pillar_meta = meta.get(pillar, {})
        target = pillar_meta.get("target_distribution")

        weekly = [0] * 12
        for p in posts:  # full history for the sparkline, not range-limited
            if p.pillar != pillar or p.date is None:
                continue
            d = p.date.date()
            for i in range(12):
                if week_starts[i] <= d <= week_starts[i] + timedelta(days=6):
                    weekly[i] += 1
                    break

        pillar_stats.append(
            {
                "pillar": pillar,
                "color": pillar_meta.get("color"),
                "posts": len(group),
                "engagement": engagement,
                "rate": round(rate, 2) if rate is not None else None,
                "target_pct": round(target * 100, 1) if target is not None else None,
                "actual_pct": round(len(group) / total_posts * 100, 1) if total_posts else 0.0,
                "weekly_series": weekly,
            }
        )

    return {
        "pillars": pillar_stats,
        "insights": compute_pillar_insights(pillar_stats),
    }


def get_platforms(
    db_path: str, range_key: str = DEFAULT_RANGE, now: datetime | None = None
) -> dict:
    """GET /api/analytics/platforms payload."""
    now = now or utcnow()
    all_records = fetch_platform_records(db_path)
    days = resolve_days(range_key, all_records, now)
    start, end = window_dates(now, days)

    records = records_in_window(all_records, start, end)

    groups: dict[str, list[PlatformRecord]] = {}
    for r in records:
        if r.platform:
            groups.setdefault(r.platform, []).append(r)

    platforms = []
    for platform, group in sorted(groups.items(), key=lambda kv: -sum(r.engagement for r in kv[1])):
        engagement = sum(r.engagement for r in group)
        reach = sum(r.reach for r in group)
        platforms.append(
            {
                "platform": platform,
                "posts": len(group),
                "engagement": engagement,
                "reach": reach,
                "rate": round(engagement / reach * 100, 2) if reach > 0 else None,
            }
        )

    return {"platforms": platforms, "heatmap": compute_heatmap(records)}


def _week_label(week_start: date, week_end: date) -> str:
    """Label like 'Mar 3–9' (or 'Mar 30–Apr 5' across months)."""
    if week_start.month == week_end.month:
        return f"{week_start.strftime('%b')} {week_start.day}–{week_end.day}"
    return f"{week_start.strftime('%b')} {week_start.day}–{week_end.strftime('%b')} {week_end.day}"


def _load_festivals(calendar_path: Path) -> list[dict]:
    if not calendar_path.exists():
        return []
    try:
        return json.loads(calendar_path.read_text())
    except (json.JSONDecodeError, OSError):
        logger.warning("Could not load festival calendar at %s", calendar_path)
        return []


def get_rhythm(
    db_path: str,
    range_key: str = DEFAULT_RANGE,
    now: datetime | None = None,
    calendar_path: Path | None = None,
) -> dict:
    """GET /api/analytics/rhythm payload."""
    now = now or utcnow()
    calendar_path = calendar_path or _DEFAULT_CALENDAR_PATH

    records = fetch_platform_records(db_path)
    posts = aggregate_posts(records)
    days = resolve_days(range_key, records, now)
    start, end = window_dates(now, days)
    current = posts_in_window(posts, start, end)

    # Weeks: Monday-start calendar weeks covering the window.
    weeks = []
    week_start = start - timedelta(days=start.weekday())
    while week_start <= end:
        week_end = week_start + timedelta(days=6)
        posted = sum(
            1 for p in current if p.date is not None and week_start <= p.date.date() <= week_end
        )
        weeks.append(
            {
                "label": _week_label(week_start, week_end),
                # ISO Monday date so clients can bucket by calendar month
                # without re-deriving dates from their own (non-UTC) clock.
                "week_start": week_start.isoformat(),
                "posted": posted,
                # No cadence setting exists today — target is null, never invented.
                "target": None,
            }
        )
        week_start += timedelta(days=7)

    # Festivals inside [window start, now + 30d].
    overall_avg = sum(p.engagement for p in current) / len(current) if current else None
    festivals = []
    horizon = now.date() + timedelta(days=30)
    for fest in _load_festivals(calendar_path):
        try:
            fest_date = datetime.strptime(fest["date"], "%Y-%m-%d").date()
        except (KeyError, ValueError):
            continue
        if not (start <= fest_date <= horizon):
            continue
        nearby = [
            p for p in posts if p.date is not None and abs((p.date.date() - fest_date).days) <= 2
        ]
        lift_pct = None
        if nearby and overall_avg:
            fest_avg = sum(p.engagement for p in nearby) / len(nearby)
            lift_pct = round((fest_avg / overall_avg - 1) * 100, 1)
        festivals.append(
            {
                "date": fest_date.isoformat(),
                "name": fest.get("name", ""),
                "posts": len(nearby),
                "lift_pct": lift_pct,
                "pending": fest_date > now.date(),
            }
        )

    # Season summary.
    heatmap = compute_heatmap(records_in_window(records, start, end))
    best_slot = None
    if heatmap["peak"] is not None:
        best_slot = {
            "day": DAY_NAMES[heatmap["peak"]["day"]],
            "hour_bucket": HOUR_BUCKET_LABELS[heatmap["peak"]["bucket"]],
        }

    lead_days = [
        (p.date - p.created_at).total_seconds() / 86400
        for p in current
        if p.source == "app" and p.date is not None and p.created_at is not None
    ]
    avg_lead_days = round(sum(lead_days) / len(lead_days), 1) if lead_days else None

    return {
        "weeks": weeks,
        "festivals": festivals,
        "season": {
            "total_posts": len(current),
            "consistency": {
                # No cadence targets exist yet — on_target_weeks is null.
                "on_target_weeks": None,
                "total_weeks": len(weeks),
            },
            "best_slot": best_slot,
            "avg_lead_days": avg_lead_days,
        },
    }


def get_hashtags(db_path: str, platform: str | None = None, count: int = 8) -> dict:
    """GET /api/analytics/hashtags payload.

    Reads hashtag_performance; when the table is empty it is lazily
    populated from social_history via HashtagTracker.update_performance
    (source="history" in that case). When a platform filter yields no
    rows, falls back to the best-performing hashtags across all
    platforms (social_history currently only holds facebook data).
    """
    from content_engine.analytics.hashtag_tracker import HashtagTracker

    conn = _connect(db_path)
    source = "performance"

    def _count_all() -> int:
        try:
            return conn.execute("SELECT COUNT(*) FROM hashtag_performance").fetchone()[0]
        except sqlite3.OperationalError:
            return 0

    if _count_all() == 0:
        conn.close()
        try:
            HashtagTracker(db_path).update_performance()
        except sqlite3.Error as e:
            logger.warning("Lazy hashtag populate failed: %s", e)
        source = "history"
        conn = _connect(db_path)

    def _read(platform_filter: str | None) -> list[sqlite3.Row]:
        try:
            if platform_filter:
                return conn.execute(
                    """SELECT hashtag, avg_engagement, times_used, trend
                       FROM hashtag_performance WHERE platform = ?
                       ORDER BY avg_engagement DESC LIMIT ?""",
                    (platform_filter, count),
                ).fetchall()
            return conn.execute(
                """SELECT hashtag, avg_engagement, times_used, trend
                   FROM hashtag_performance
                   ORDER BY avg_engagement DESC LIMIT ?""",
                (count,),
            ).fetchall()
        except sqlite3.OperationalError:
            return []

    rows = _read(platform)
    if platform and not rows:
        rows = _read(None)  # cross-platform fallback
    conn.close()

    return {
        "hashtags": [
            {
                "hashtag": r["hashtag"],
                "avg_engagement": round(r["avg_engagement"] or 0.0, 2),
                "times_used": r["times_used"] or 0,
                "trend": r["trend"] or "stable",
            }
            for r in rows
        ],
        "source": source,
    }
