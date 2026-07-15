"""Tests for the converged Postiz analytics sync (single fetch via PostizClient)."""

import json
import sqlite3
from unittest.mock import MagicMock

import pytest

from content_engine.analytics.postiz_sync import (
    PostizAnalyticsSync,
    _collect_sync_targets,
    sync_all,
)
from content_engine.postiz import PostizAPIError

SAMPLE_ANALYTICS = {
    "likes": 45,
    "comments": 8,
    "shares": 12,
    "reach": 500,
    "impressions": 1200,
}


def make_client(**kwargs) -> MagicMock:
    client = MagicMock()
    client.fetch_post_analytics.return_value = dict(SAMPLE_ANALYTICS)
    for key, value in kwargs.items():
        setattr(client, key, value)
    return client


class TestPostizAnalyticsSyncInit:
    def test_wraps_postiz_client(self):
        client = make_client()
        sync = PostizAnalyticsSync(client=client)
        assert sync.client is client

    def test_rate_limit_default(self):
        sync = PostizAnalyticsSync(client=make_client())
        assert sync.rate_limit == 30


class TestRateLimiting:
    def test_tracks_request_count(self):
        sync = PostizAnalyticsSync(client=make_client())
        assert sync.request_count == 0

    def test_is_rate_limited_under_limit(self):
        sync = PostizAnalyticsSync(client=make_client())
        sync.request_count = 5
        assert not sync.is_rate_limited

    def test_is_rate_limited_at_limit(self):
        sync = PostizAnalyticsSync(client=make_client())
        sync.request_count = 30
        assert sync.is_rate_limited

    def test_fetch_increments_budget(self):
        sync = PostizAnalyticsSync(client=make_client())
        sync.fetch_post_analytics("p1")
        sync.fetch_post_analytics("p2")
        assert sync.request_count == 2


class TestFetchAnalytics:
    def test_fetch_delegates_to_client_canonical_call(self):
        client = make_client()
        sync = PostizAnalyticsSync(client=client)

        result = sync.fetch_post_analytics("post_123")

        client.fetch_post_analytics.assert_called_once_with("post_123")
        assert result["likes"] == 45
        assert result["reach"] == 500

    def test_fetch_returns_none_on_api_error(self):
        client = make_client()
        client.fetch_post_analytics.side_effect = PostizAPIError("Server error 500")
        sync = PostizAnalyticsSync(client=client)

        assert sync.fetch_post_analytics("missing") is None

    def test_fetch_reraises_rate_limit_errors(self):
        client = make_client()
        client.fetch_post_analytics.side_effect = PostizAPIError("Rate limit after 3 attempts")
        sync = PostizAnalyticsSync(client=client)

        with pytest.raises(PostizAPIError, match="Rate limit"):
            sync.fetch_post_analytics("p1")


# --- DB storage ---


@pytest.fixture
def analytics_db(tmp_path):
    """Temporary SQLite with content_rows + analytics_cache tables."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE content_rows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_text TEXT,
            pillar TEXT,
            postiz_ids TEXT,
            posted_at DATETIME,
            date DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
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
        );
        CREATE TABLE social_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            external_id TEXT NOT NULL,
            post_text TEXT,
            hashtags TEXT,
            posted_at DATETIME,
            likes INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            reach INTEGER DEFAULT 0,
            pillar TEXT,
            imported_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(platform, external_id)
        );
        CREATE TABLE hashtag_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hashtag TEXT NOT NULL,
            platform TEXT NOT NULL,
            times_used INTEGER NOT NULL,
            total_engagement INTEGER NOT NULL,
            avg_engagement REAL NOT NULL,
            trend TEXT NOT NULL,
            updated_at DATETIME NOT NULL,
            UNIQUE(hashtag, platform)
        );
    """)
    conn.commit()
    conn.close()
    return db_path


class TestUpsertAnalytics:
    def test_inserts_new_record(self, analytics_db):
        sync = PostizAnalyticsSync(client=make_client())
        sync.upsert_analytics_sync(
            str(analytics_db),
            content_row_id=1,
            platform="instagram",
            postiz_post_id="p_123",
            analytics=SAMPLE_ANALYTICS,
        )

        conn = sqlite3.connect(str(analytics_db))
        row = conn.execute(
            "SELECT likes, impressions FROM analytics_cache WHERE postiz_post_id = 'p_123'"
        ).fetchone()
        conn.close()
        assert row == (45, 1200)

    def test_upserts_existing(self, analytics_db):
        sync = PostizAnalyticsSync(client=make_client())
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


class TestCollectSyncTargets:
    def _insert_row(self, db_path, postiz_ids):
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT INTO content_rows (raw_text, postiz_ids) VALUES (?, ?)", ("post", postiz_ids)
        )
        conn.commit()
        conn.close()

    def test_parses_platform_map(self, analytics_db):
        self._insert_row(analytics_db, json.dumps({"instagram": "pz_1", "facebook": "pz_2"}))
        targets, skipped = _collect_sync_targets(str(analytics_db))
        assert skipped == 0
        assert sorted(t[1:] for t in targets) == [
            ("facebook", "pz_2"),
            ("instagram", "pz_1"),
        ]

    def test_skips_legacy_comma_format(self, analytics_db):
        self._insert_row(analytics_db, "pz_1,pz_2")
        targets, skipped = _collect_sync_targets(str(analytics_db))
        assert targets == []
        assert skipped == 1

    def test_ignores_rows_without_postiz_ids(self, analytics_db):
        self._insert_row(analytics_db, None)
        targets, skipped = _collect_sync_targets(str(analytics_db))
        assert targets == []
        assert skipped == 0


class TestSyncAll:
    def _insert_row(self, db_path, postiz_ids):
        conn = sqlite3.connect(str(db_path))
        cur = conn.execute(
            "INSERT INTO content_rows (raw_text, postiz_ids) VALUES (?, ?)",
            ("post", postiz_ids),
        )
        conn.commit()
        conn.close()
        return cur.lastrowid

    def test_zero_eligible_rows_is_safe_without_client(self, analytics_db):
        """No postiz_ids anywhere → no client needed, clean empty result."""
        result = sync_all(str(analytics_db), client=None)
        assert result == {"synced": 0, "failed": 0, "skipped": 0, "rate_limited": False}

    def test_syncs_platform_map_rows(self, analytics_db):
        row_id = self._insert_row(
            analytics_db, json.dumps({"instagram": "pz_1", "facebook": "pz_2"})
        )
        client = make_client()

        result = sync_all(str(analytics_db), client=client)

        assert result["synced"] == 2
        assert result["failed"] == 0
        assert result["rate_limited"] is False

        conn = sqlite3.connect(str(analytics_db))
        rows = conn.execute(
            "SELECT content_row_id, platform, postiz_post_id, likes FROM analytics_cache"
        ).fetchall()
        conn.close()
        assert (row_id, "instagram", "pz_1", 45) in rows
        assert (row_id, "facebook", "pz_2", 45) in rows

    def test_counts_failures_and_continues(self, analytics_db):
        self._insert_row(analytics_db, json.dumps({"instagram": "pz_1", "facebook": "pz_2"}))
        client = make_client()
        client.fetch_post_analytics.side_effect = [
            PostizAPIError("Server error 500"),
            dict(SAMPLE_ANALYTICS),
        ]

        result = sync_all(str(analytics_db), client=client)

        assert result["synced"] == 1
        assert result["failed"] == 1
        assert result["rate_limited"] is False

    def test_stops_when_budget_exhausted(self, analytics_db):
        self._insert_row(
            analytics_db,
            json.dumps({"instagram": "pz_1", "facebook": "pz_2", "tiktok": "pz_3"}),
        )
        client = make_client()

        result = sync_all(str(analytics_db), client=client, rate_limit=2)

        assert result["synced"] == 2
        assert result["skipped"] == 1
        assert result["rate_limited"] is True
        assert client.fetch_post_analytics.call_count == 2

    def test_stops_on_persistent_429(self, analytics_db):
        self._insert_row(
            analytics_db,
            json.dumps({"instagram": "pz_1", "facebook": "pz_2", "tiktok": "pz_3"}),
        )
        client = make_client()
        client.fetch_post_analytics.side_effect = PostizAPIError("Rate limit after 3 attempts")

        result = sync_all(str(analytics_db), client=client)

        assert result["synced"] == 0
        assert result["failed"] == 1
        assert result["skipped"] == 2
        assert result["rate_limited"] is True
        assert client.fetch_post_analytics.call_count == 1

    def test_refreshes_hashtag_performance_from_history(self, analytics_db):
        conn = sqlite3.connect(str(analytics_db))
        conn.execute(
            """INSERT INTO social_history (platform, external_id, post_text,
                                           hashtags, likes, comments, shares)
               VALUES ('facebook', 'fb_1', 'Cows', '["GitaValley"]', 10, 2, 1)"""
        )
        conn.commit()
        conn.close()

        sync_all(str(analytics_db), client=None)

        conn = sqlite3.connect(str(analytics_db))
        row = conn.execute(
            "SELECT times_used, total_engagement FROM hashtag_performance "
            "WHERE hashtag='GitaValley' AND platform='facebook'"
        ).fetchone()
        conn.close()
        assert row == (1, 13)

    def test_no_client_configured_counts_failed(self, analytics_db, monkeypatch):
        monkeypatch.delenv("POSTIZ_API_KEY", raising=False)
        self._insert_row(analytics_db, json.dumps({"instagram": "pz_1"}))

        result = sync_all(str(analytics_db), client=None)

        assert result["failed"] == 1
        assert result["synced"] == 0
