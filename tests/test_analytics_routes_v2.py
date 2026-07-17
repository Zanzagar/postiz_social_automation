"""Route tests for the v2 /api/analytics endpoints (unified data set).

Clock is frozen via the get_now dependency override — never wall-clock.
All Postiz HTTP is mocked.
"""

import json
import sqlite3
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from api.auth import get_current_user
from api.main import app
from api.routes.analytics import get_db_path, get_now

FROZEN_NOW = datetime(2026, 7, 14, 12, 0, 0)

SCHEMA = """
    CREATE TABLE content_rows (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date DATETIME,
        pillar TEXT,
        raw_text TEXT,
        platforms TEXT,
        status TEXT DEFAULT 'draft',
        postiz_ids TEXT,
        posted_at DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE analytics_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content_row_id INTEGER REFERENCES content_rows(id),
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
        media_urls TEXT,
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
    CREATE TABLE pillars (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(100) UNIQUE NOT NULL,
        color VARCHAR(20),
        target_distribution FLOAT
    );
"""


def _make_db(path, script=""):
    conn = sqlite3.connect(str(path))
    conn.executescript(SCHEMA)
    if script:
        conn.executescript(script)
    conn.commit()
    conn.close()
    return str(path)


@pytest.fixture
def empty_db(tmp_path):
    return _make_db(tmp_path / "empty.db")


@pytest.fixture
def history_only_db(tmp_path):
    """Only social_history data — no app posts (analytics_cache empty)."""
    return _make_db(
        tmp_path / "history.db",
        """
        INSERT INTO social_history (platform, external_id, post_text, hashtags, posted_at,
                                    likes, comments, shares, reach, pillar)
        VALUES ('facebook', 'fb_1', 'Morning kirtan by the barn', '["GitaValley"]',
                '2026-07-07T18:30:00+0000', 40, 6, 4, 400, 'Community');
        INSERT INTO social_history (platform, external_id, post_text, hashtags, posted_at,
                                    likes, comments, shares, reach, pillar)
        VALUES ('facebook', 'fb_2', 'Hay harvest complete', '[]',
                '2026-07-10T09:15:00+0000', 20, 2, 2, 300, NULL);
        """,
    )


@pytest.fixture
def client_for(empty_db):
    """Factory: yields an AsyncClient factory bound to a db path."""

    def _bind(db_path: str):
        app.dependency_overrides[get_current_user] = lambda: {"sub": "testuser"}
        app.dependency_overrides[get_db_path] = lambda: db_path
        app.dependency_overrides[get_now] = lambda: FROZEN_NOW
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    yield _bind
    app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestSummaryRoute:
    async def test_empty_db_well_formed(self, client_for, empty_db):
        async with client_for(empty_db) as client:
            resp = await client.get("/api/analytics/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["range"] == "30d"
        assert set(data["kpis"]) == {"posts", "engagement", "avg_rate", "reach"}
        assert data["kpis"]["posts"]["value"] == 0
        assert data["kpis"]["posts"]["delta_pct"] is None
        assert data["top_post"] is None
        assert data["insights"] == []
        assert data["sources"] == {"app": 0, "history": 0}

    async def test_history_only_data(self, client_for, history_only_db):
        async with client_for(history_only_db) as client:
            resp = await client.get("/api/analytics/summary?range=30d")
        assert resp.status_code == 200
        data = resp.json()
        assert data["kpis"]["posts"]["value"] == 2
        assert data["sources"] == {"app": 0, "history": 2}
        assert data["top_post"]["source"] == "history"
        assert data["top_post"]["engagement"] == 50

    async def test_invalid_range_rejected(self, client_for, empty_db):
        async with client_for(empty_db) as client:
            resp = await client.get("/api/analytics/summary?range=14d")
        assert resp.status_code == 422

    async def test_range_echoed(self, client_for, empty_db):
        async with client_for(empty_db) as client:
            resp = await client.get("/api/analytics/summary?range=90d")
        assert resp.json()["range"] == "90d"


@pytest.mark.asyncio
class TestPostsRoute:
    async def test_empty_db(self, client_for, empty_db):
        async with client_for(empty_db) as client:
            resp = await client.get("/api/analytics/posts")
        assert resp.status_code == 200
        assert resp.json() == {"posts": [], "total": 0}

    async def test_history_only_sorted(self, client_for, history_only_db):
        async with client_for(history_only_db) as client:
            resp = await client.get("/api/analytics/posts?range=30d")
        data = resp.json()
        assert data["total"] == 2
        assert data["posts"][0]["engagement"] == 50
        assert data["posts"][0]["source"] == "history"
        assert data["posts"][0]["platforms"] == ["facebook"]
        assert data["posts"][0]["trend"] in {"up", "down", "flat"}

    async def test_pagination_params(self, client_for, history_only_db):
        async with client_for(history_only_db) as client:
            resp = await client.get("/api/analytics/posts?limit=1&offset=1")
        data = resp.json()
        assert len(data["posts"]) == 1
        assert data["total"] == 2

    async def test_limit_above_cap_rejected(self, client_for, empty_db):
        """limit is capped at 100 — the frontend pages at 100, so 500 must 422."""
        async with client_for(empty_db) as client:
            resp = await client.get("/api/analytics/posts?limit=500")
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestPillarInsightsRoute:
    async def test_empty_db(self, client_for, empty_db):
        async with client_for(empty_db) as client:
            resp = await client.get("/api/analytics/pillar-insights")
        assert resp.status_code == 200
        assert resp.json() == {"pillars": [], "insights": []}

    async def test_history_only_pillars(self, client_for, history_only_db):
        conn = sqlite3.connect(history_only_db)
        conn.execute(
            "INSERT INTO pillars (name, color, target_distribution) VALUES (?, ?, ?)",
            ("Community", "#7c3aed", 0.25),
        )
        conn.commit()
        conn.close()

        async with client_for(history_only_db) as client:
            resp = await client.get("/api/analytics/pillar-insights")
        data = resp.json()
        assert len(data["pillars"]) == 1
        pillar = data["pillars"][0]
        assert pillar["pillar"] == "Community"
        assert pillar["color"] == "#7c3aed"
        assert pillar["target_pct"] == 25.0
        assert pillar["actual_pct"] == 50.0  # 1 of 2 posts
        assert len(pillar["weekly_series"]) == 12


@pytest.mark.asyncio
class TestPlatformsRoute:
    async def test_empty_db(self, client_for, empty_db):
        async with client_for(empty_db) as client:
            resp = await client.get("/api/analytics/platforms")
        assert resp.status_code == 200
        data = resp.json()
        assert data["platforms"] == []
        assert data["heatmap"]["peak"] is None
        assert data["heatmap"]["sample_size"] == 0
        assert len(data["heatmap"]["days"]) == 7
        assert data["heatmap"]["hour_buckets"] == ["6a", "9a", "12p", "3p", "6p", "9p"]

    async def test_history_only_heatmap(self, client_for, history_only_db, monkeypatch):
        monkeypatch.setenv("GV_DISPLAY_TZ", "America/New_York")
        async with client_for(history_only_db) as client:
            resp = await client.get("/api/analytics/platforms?range=30d")
        data = resp.json()
        assert data["platforms"][0]["platform"] == "facebook"
        assert data["platforms"][0]["posts"] == 2
        assert data["heatmap"]["sample_size"] == 2
        # fb_1: Tue Jul 7 18:30 UTC = 14:30 ET → day 1, bucket 3 (3p);
        # higher engagement → peak
        assert data["heatmap"]["peak"] == {"day": 1, "bucket": 3}
        # No invented fields
        assert "followers" not in json.dumps(data)
        assert "sentiment" not in json.dumps(data)


@pytest.mark.asyncio
class TestRhythmRoute:
    async def test_empty_db(self, client_for, empty_db):
        async with client_for(empty_db) as client:
            resp = await client.get("/api/analytics/rhythm")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["weeks"]) >= 4
        assert all(w["target"] is None for w in data["weeks"])
        assert data["season"]["total_posts"] == 0
        assert data["season"]["best_slot"] is None
        assert data["season"]["consistency"]["on_target_weeks"] is None

    async def test_history_only(self, client_for, history_only_db):
        async with client_for(history_only_db) as client:
            resp = await client.get("/api/analytics/rhythm?range=30d")
        data = resp.json()
        assert data["season"]["total_posts"] == 2
        # History posts have no created_at lead time
        assert data["season"]["avg_lead_days"] is None
        assert data["season"]["best_slot"] is not None


@pytest.mark.asyncio
class TestSyncRoute:
    async def test_sync_with_zero_eligible_rows(self, client_for, empty_db, monkeypatch):
        """Placeholder API key + no postiz_ids rows → clean empty result."""
        monkeypatch.setenv("JWT_SECRET", "test-secret-key-min-32-chars-long!!")
        monkeypatch.setenv("API_PASSWORD", "pw")
        monkeypatch.setenv("POSTIZ_API_KEY", "placeholder-key")
        monkeypatch.setenv("SPREADSHEET_ID", "sheet")
        from api.dependencies import get_settings

        get_settings.cache_clear()
        try:
            async with client_for(empty_db) as client:
                resp = await client.post("/api/analytics/sync")
        finally:
            get_settings.cache_clear()

        assert resp.status_code == 200
        assert resp.json() == {
            "synced": 0,
            "failed": 0,
            "skipped": 0,
            "rate_limited": False,
        }

    async def test_sync_writes_analytics_cache(self, client_for, empty_db, monkeypatch):
        monkeypatch.setenv("JWT_SECRET", "test-secret-key-min-32-chars-long!!")
        monkeypatch.setenv("API_PASSWORD", "pw")
        monkeypatch.setenv("POSTIZ_API_KEY", "placeholder-key")
        monkeypatch.setenv("SPREADSHEET_ID", "sheet")
        from api.dependencies import get_settings

        get_settings.cache_clear()

        conn = sqlite3.connect(empty_db)
        conn.execute(
            "INSERT INTO content_rows (raw_text, postiz_ids) VALUES (?, ?)",
            ("post", json.dumps({"instagram": "pz_1"})),
        )
        conn.commit()
        conn.close()

        mock_client = MagicMock()
        mock_client.fetch_post_analytics.return_value = {
            "likes": 12,
            "comments": 3,
            "shares": 1,
            "reach": 200,
            "impressions": 400,
        }

        try:
            with patch("content_engine.postiz.PostizClient", return_value=mock_client):
                async with client_for(empty_db) as client:
                    resp = await client.post("/api/analytics/sync")
        finally:
            get_settings.cache_clear()

        assert resp.status_code == 200
        data = resp.json()
        assert data["synced"] == 1
        assert data["rate_limited"] is False

        conn = sqlite3.connect(empty_db)
        row = conn.execute(
            "SELECT platform, likes, impressions FROM analytics_cache WHERE postiz_post_id='pz_1'"
        ).fetchone()
        conn.close()
        assert row == ("instagram", 12, 400)


@pytest.mark.asyncio
class TestHashtagsRoute:
    async def test_empty_db(self, client_for, empty_db):
        async with client_for(empty_db) as client:
            resp = await client.get("/api/analytics/hashtags")
        assert resp.status_code == 200
        assert resp.json() == {"hashtags": [], "source": "history"}

    async def test_lazy_populate_from_history(self, client_for, history_only_db):
        async with client_for(history_only_db) as client:
            resp = await client.get("/api/analytics/hashtags?platform=facebook")
        data = resp.json()
        assert data["source"] == "history"
        assert data["hashtags"][0]["hashtag"] == "GitaValley"
        assert data["hashtags"][0]["times_used"] == 1

    async def test_count_param(self, client_for, history_only_db):
        async with client_for(history_only_db) as client:
            resp = await client.get("/api/analytics/hashtags?count=1")
        assert len(resp.json()["hashtags"]) <= 1


@pytest.mark.asyncio
class TestLegacyEndpointsUnchanged:
    """The 3 pre-existing endpoints keep their exact shapes."""

    async def test_overview_shape(self, client_for, empty_db):
        async with client_for(empty_db) as client:
            resp = await client.get("/api/analytics/overview")
        assert resp.status_code == 200
        assert set(resp.json()) == {
            "total_posts",
            "total_engagement",
            "avg_engagement",
            "total_reach",
            "total_impressions",
        }

    async def test_pillars_shape(self, client_for, empty_db):
        async with client_for(empty_db) as client:
            resp = await client.get("/api/analytics/pillars")
        assert resp.status_code == 200
        assert resp.json() == {"pillars": []}

    async def test_top_posts_shape(self, client_for, empty_db):
        async with client_for(empty_db) as client:
            resp = await client.get("/api/analytics/top-posts")
        assert resp.status_code == 200
        assert resp.json() == {"posts": []}


@pytest.mark.asyncio
class TestAllRangeRoutes:
    """range=all accepted by all 5 v2 endpoints — no lower time bound."""

    @pytest.fixture
    def old_history_db(self, tmp_path):
        """history_only_db data plus a 2022 row outside every fixed range."""
        return _make_db(
            tmp_path / "old_history.db",
            """
            INSERT INTO social_history (platform, external_id, post_text, hashtags, posted_at,
                                        likes, comments, shares, reach, pillar)
            VALUES ('facebook', 'fb_1', 'Morning kirtan by the barn', '["GitaValley"]',
                    '2026-07-07T18:30:00+0000', 40, 6, 4, 400, 'Community');
            INSERT INTO social_history (platform, external_id, post_text, hashtags, posted_at,
                                        likes, comments, shares, reach, pillar)
            VALUES ('facebook', 'fb_2', 'Hay harvest complete', '[]',
                    '2026-07-10T09:15:00+0000', 20, 2, 2, 300, NULL);
            INSERT INTO social_history (platform, external_id, post_text, hashtags, posted_at,
                                        likes, comments, shares, reach, pillar)
            VALUES ('facebook', 'fb_old', 'Old post from 2022', '[]',
                    '2022-05-25T17:12:15+0000', 100, 10, 10, 1000, NULL);
            """,
        )

    async def test_all_accepted_on_all_five_endpoints(self, client_for, empty_db):
        async with client_for(empty_db) as client:
            for path in ("summary", "posts", "pillar-insights", "platforms", "rhythm"):
                resp = await client.get(f"/api/analytics/{path}?range=all")
                assert resp.status_code == 200, path

    async def test_old_rows_appear_at_all_absent_at_30d(self, client_for, old_history_db):
        async with client_for(old_history_db) as client:
            all_resp = await client.get("/api/analytics/summary?range=all")
            d30_resp = await client.get("/api/analytics/summary?range=30d")
        assert all_resp.status_code == 200
        assert all_resp.json()["range"] == "all"
        assert all_resp.json()["kpis"]["posts"]["value"] == 3
        assert d30_resp.json()["kpis"]["posts"]["value"] == 2

    async def test_posts_endpoint_returns_old_rows_at_all(self, client_for, old_history_db):
        async with client_for(old_history_db) as client:
            resp = await client.get("/api/analytics/posts?range=all")
        data = resp.json()
        assert data["total"] == 3
        assert any(p["engagement"] == 120 for p in data["posts"])  # fb_old

    async def test_invalid_range_still_rejected(self, client_for, empty_db):
        async with client_for(empty_db) as client:
            resp = await client.get("/api/analytics/summary?range=everything")
        assert resp.status_code == 422
