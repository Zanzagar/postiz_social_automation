"""Postiz analytics sync — converged on PostizClient's canonical fetch.

Single fetch implementation: PostizClient.fetch_post_analytics
(``GET /analytics/post/{postId}``, POSTIZ_CONTRACT.md §7 / I2 resolved).
This module adds rate-limit budgeting (30 req/h shared across all Postiz
usage) and the analytics_cache upsert, plus the module-level ``sync_all``
entry point used by ``POST /api/analytics/sync``.
"""

import json
import logging
import os
import sqlite3
from datetime import UTC, datetime

from content_engine.postiz import ANALYTICS_FIELDS, PostizAPIError, PostizClient

logger = logging.getLogger(__name__)

DEFAULT_RATE_LIMIT = 30


class PostizAnalyticsSync:
    """Fetch engagement data from Postiz and cache it in analytics_cache.

    Wraps a PostizClient (the single canonical fetch implementation) and
    enforces a request budget instead of sleeping: when the budget is
    exhausted the caller stops and reports ``rate_limited`` — safe for
    use inside a web request.
    """

    def __init__(self, client: PostizClient, rate_limit: int = DEFAULT_RATE_LIMIT):
        self.client = client
        self.rate_limit = rate_limit
        self.request_count = 0

    @property
    def is_rate_limited(self) -> bool:
        """True when the hourly request budget is exhausted."""
        return self.request_count >= self.rate_limit

    def fetch_post_analytics(self, postiz_post_id: str) -> dict | None:
        """Fetch canonical analytics for one post; None on API failure.

        Increments the request budget on every attempt. Raises
        PostizAPIError only for rate-limit exhaustion signalled by the
        API itself (persistent 429) so the caller can stop the run.
        """
        self.request_count += 1
        try:
            return self.client.fetch_post_analytics(postiz_post_id)
        except PostizAPIError as e:
            if "Rate limit" in str(e):
                raise
            logger.warning("Postiz analytics fetch failed for %s: %s", postiz_post_id, e)
            return None
        except Exception as e:
            logger.warning("Postiz analytics fetch failed for %s: %s", postiz_post_id, e)
            return None

    def upsert_analytics_sync(
        self,
        db_path: str,
        content_row_id: int,
        platform: str,
        postiz_post_id: str,
        analytics: dict,
    ) -> None:
        """Insert or update an analytics_cache entry."""
        conn = sqlite3.connect(db_path)
        now = datetime.now(UTC).isoformat()
        values = {field: analytics.get(field, 0) for field in ANALYTICS_FIELDS}

        existing = conn.execute(
            "SELECT id FROM analytics_cache WHERE postiz_post_id = ?",
            (postiz_post_id,),
        ).fetchone()

        if existing:
            conn.execute(
                """UPDATE analytics_cache
                   SET likes = ?, comments = ?, shares = ?, reach = ?,
                       impressions = ?, fetched_at = ?
                   WHERE id = ?""",
                (
                    values["likes"],
                    values["comments"],
                    values["shares"],
                    values["reach"],
                    values["impressions"],
                    now,
                    existing[0],
                ),
            )
        else:
            conn.execute(
                """INSERT INTO analytics_cache
                   (content_row_id, platform, postiz_post_id, likes, comments,
                    shares, reach, impressions, fetched_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    content_row_id,
                    platform,
                    postiz_post_id,
                    values["likes"],
                    values["comments"],
                    values["shares"],
                    values["reach"],
                    values["impressions"],
                    now,
                ),
            )

        conn.commit()
        conn.close()


def _collect_sync_targets(db_path: str) -> tuple[list[tuple[int, str, str]], int]:
    """Return (targets, skipped) from content_rows with postiz_ids.

    postiz_ids is canonically a per-platform JSON map
    ``{"instagram": "postiz-id", ...}`` (POSTIZ_CONTRACT.md §7 / G1).
    Rows whose postiz_ids can't be parsed as such a map (legacy
    comma-separated strings lack platform attribution) are skipped.
    """
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT id, postiz_ids FROM content_rows "
        "WHERE postiz_ids IS NOT NULL AND TRIM(postiz_ids) != ''"
    ).fetchall()
    conn.close()

    targets: list[tuple[int, str, str]] = []
    skipped = 0
    for row_id, raw in rows:
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            parsed = None
        if isinstance(parsed, dict) and parsed:
            for platform, post_id in parsed.items():
                if post_id:
                    targets.append((row_id, str(platform), str(post_id)))
        else:
            skipped += 1
            logger.info("Skipping row %s: postiz_ids is not a platform map", row_id)
    return targets, skipped


def _client_from_env() -> PostizClient | None:
    """Build a PostizClient from POSTIZ_API_KEY / POSTIZ_BASE_URL env vars."""
    api_key = os.getenv("POSTIZ_API_KEY")
    if not api_key:
        return None
    return PostizClient(
        api_key=api_key,
        base_url=os.getenv("POSTIZ_BASE_URL", "https://postiz.sethpc.xyz/api/public/v1"),
    )


def _refresh_hashtag_performance(db_path: str) -> None:
    """Recompute hashtag_performance from social_history (best-effort)."""
    from content_engine.analytics.hashtag_tracker import HashtagTracker

    try:
        HashtagTracker(db_path).update_performance()
    except sqlite3.Error as e:
        logger.warning("Hashtag performance refresh failed: %s", e)


def sync_all(
    db_path: str,
    client: PostizClient | None = None,
    rate_limit: int = DEFAULT_RATE_LIMIT,
) -> dict:
    """Sync Postiz analytics for all content_rows with postiz_ids.

    Writes analytics_cache, then refreshes hashtag_performance from
    social_history. Rate-limit aware: stops (rather than sleeping) when
    the request budget is exhausted or the API reports persistent 429,
    reporting ``rate_limited: True`` with the untried posts counted as
    skipped. Safe to call with 0 eligible rows — no Postiz client is
    even constructed in that case.

    Returns {"synced": int, "failed": int, "skipped": int, "rate_limited": bool}.
    """
    targets, skipped = _collect_sync_targets(db_path)
    result = {"synced": 0, "failed": 0, "skipped": skipped, "rate_limited": False}

    if not targets:
        _refresh_hashtag_performance(db_path)
        return result

    if client is None:
        client = _client_from_env()
    if client is None:
        logger.error("POSTIZ_API_KEY not configured — cannot sync %d posts", len(targets))
        result["failed"] = len(targets)
        _refresh_hashtag_performance(db_path)
        return result

    sync = PostizAnalyticsSync(client=client, rate_limit=rate_limit)

    for index, (row_id, platform, post_id) in enumerate(targets):
        if sync.is_rate_limited:
            result["rate_limited"] = True
            result["skipped"] += len(targets) - index
            break

        try:
            analytics = sync.fetch_post_analytics(post_id)
        except PostizAPIError:
            # Persistent 429 from the API itself: stop the whole run.
            result["failed"] += 1
            result["rate_limited"] = True
            result["skipped"] += len(targets) - index - 1
            break

        if analytics is None:
            result["failed"] += 1
            continue

        sync.upsert_analytics_sync(db_path, row_id, platform, post_id, analytics)
        result["synced"] += 1

    _refresh_hashtag_performance(db_path)
    return result
