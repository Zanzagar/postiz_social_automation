"""Tests for Postiz analytics data pull."""

import sqlite3
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from content_engine.analytics.postiz_sync import PostizAnalyticsSync


SAMPLE_ANALYTICS = {
    "likes": 45,
    "comments": 8,
    "shares": 12,
    "reach": 500,
    "impressions": 1200,
}


class TestPostizAnalyticsSyncInit:
    def test_requires_base_url_and_api_key(self):
        sync = PostizAnalyticsSync(
            base_url="https://sethpc.xyz/api/public/v1",
            api_key="test-key",
        )
        assert "sethpc.xyz" in sync.base_url
        assert sync.api_key == "test-key"

    def test_rate_limit_default(self):
        sync = PostizAnalyticsSync(base_url="http://x", api_key="k")
        assert sync.rate_limit == 30


class TestRateLimiting:
    def test_tracks_request_count(self):
        sync = PostizAnalyticsSync(base_url="http://x", api_key="k")
        assert sync.request_count == 0

    def test_is_rate_limited_under_limit(self):
        sync = PostizAnalyticsSync(base_url="http://x", api_key="k")
        sync.request_count = 5
        assert not sync.is_rate_limited

    def test_is_rate_limited_at_limit(self):
        sync = PostizAnalyticsSync(base_url="http://x", api_key="k")
        sync.request_count = 30
        assert sync.is_rate_limited


@pytest.mark.asyncio
class TestFetchAnalytics:
    async def test_fetch_returns_analytics(self):
        sync = PostizAnalyticsSync(base_url="http://x", api_key="k")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = SAMPLE_ANALYTICS

        sync._client = MagicMock()
        sync._client.get = AsyncMock(return_value=mock_resp)

        result = await sync.fetch_post_analytics("post_123")
        assert result["likes"] == 45
        assert result["reach"] == 500
        assert sync.request_count == 1

    async def test_fetch_returns_none_on_error(self):
        sync = PostizAnalyticsSync(base_url="http://x", api_key="k")
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        sync._client = MagicMock()
        sync._client.get = AsyncMock(return_value=mock_resp)

        result = await sync.fetch_post_analytics("missing")
        assert result is None


# --- DB storage ---


@pytest.fixture
def analytics_db(tmp_path):
    """Temporary SQLite with analytics_cache table."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE analytics_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_row_id INTEGER,
            platform TEXT NOT NULL,
            postiz_post_id TEXT,
            likes INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            reach INTEGER DEFAULT 0,
            impressions INTEGER DEFAULT 0,
            fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    return db_path


class TestUpsertAnalytics:
    def test_inserts_new_record(self, analytics_db):
        sync = PostizAnalyticsSync(base_url="http://x", api_key="k")
        sync.upsert_analytics_sync(
            str(analytics_db),
            content_row_id=1,
            platform="instagram",
            postiz_post_id="p_123",
            analytics=SAMPLE_ANALYTICS,
        )

        conn = sqlite3.connect(str(analytics_db))
        row = conn.execute(
            "SELECT * FROM analytics_cache WHERE postiz_post_id = 'p_123'"
        ).fetchone()
        conn.close()
        assert row is not None

    def test_upserts_existing(self, analytics_db):
        sync = PostizAnalyticsSync(base_url="http://x", api_key="k")
        sync.upsert_analytics_sync(str(analytics_db), 1, "instagram", "p_123", SAMPLE_ANALYTICS)
        updated = {**SAMPLE_ANALYTICS, "likes": 100}
        sync.upsert_analytics_sync(str(analytics_db), 1, "instagram", "p_123", updated)

        conn = sqlite3.connect(str(analytics_db))
        rows = conn.execute(
            "SELECT likes FROM analytics_cache WHERE postiz_post_id = 'p_123'"
        ).fetchall()
        conn.close()
        # Should have only 1 row with updated likes
        assert len(rows) == 1
        assert rows[0][0] == 100
