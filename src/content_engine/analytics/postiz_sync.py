"""Postiz analytics data pull with rate limiting."""

import logging
import sqlite3
import time
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)


class PostizAnalyticsSync:
    """Fetch engagement data from Postiz API and cache locally."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        rate_limit: int = 30,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.rate_limit = rate_limit
        self.request_count = 0
        self._hour_start = time.time()
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={"Authorization": api_key},
        )

    @property
    def is_rate_limited(self) -> bool:
        """Check if we've hit the hourly rate limit."""
        return self.request_count >= self.rate_limit

    async def _check_rate_limit(self) -> None:
        """Wait if rate limited."""
        if self.is_rate_limited:
            elapsed = time.time() - self._hour_start
            if elapsed < 3600:
                import asyncio

                wait = 3600 - elapsed
                logger.info("Rate limited, waiting %.0fs", wait)
                await asyncio.sleep(wait)
            self.request_count = 0
            self._hour_start = time.time()

    async def fetch_post_analytics(self, postiz_post_id: str) -> dict | None:
        """Fetch analytics for a single Postiz post."""
        await self._check_rate_limit()

        resp = await self._client.get(f"{self.base_url}/posts/{postiz_post_id}/analytics")
        self.request_count += 1

        if resp.status_code != 200:
            logger.warning("Postiz analytics %d for post %s", resp.status_code, postiz_post_id)
            return None

        return resp.json()

    def upsert_analytics_sync(
        self,
        db_path: str,
        content_row_id: int,
        platform: str,
        postiz_post_id: str,
        analytics: dict,
    ) -> None:
        """Insert or update analytics cache entry."""
        conn = sqlite3.connect(db_path)
        now = datetime.now(timezone.utc).isoformat()

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
                    analytics.get("likes", 0),
                    analytics.get("comments", 0),
                    analytics.get("shares", 0),
                    analytics.get("reach", 0),
                    analytics.get("impressions", 0),
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
                    analytics.get("likes", 0),
                    analytics.get("comments", 0),
                    analytics.get("shares", 0),
                    analytics.get("reach", 0),
                    analytics.get("impressions", 0),
                    now,
                ),
            )

        conn.commit()
        conn.close()

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
