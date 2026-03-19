"""Tests for analytics correlation engine."""

import sqlite3

import pytest

from content_engine.analytics.correlation import AnalyticsEngine


@pytest.fixture
def engine_db(tmp_path):
    """Temporary SQLite with analytics and content data."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE content_rows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            content_pillar TEXT,
            raw_text TEXT,
            platforms TEXT,
            status TEXT DEFAULT 'draft',
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
        INSERT INTO content_rows (id, date, content_pillar, raw_text, status)
        VALUES (1, '2026-03-01', 'Cow Life', 'Our cows love sunrise', 'posted');
        INSERT INTO content_rows (id, date, content_pillar, raw_text, status)
        VALUES (2, '2026-03-02', 'Community', 'Sunday Feast this week', 'posted');
        INSERT INTO content_rows (id, date, content_pillar, raw_text, status)
        VALUES (3, '2026-03-05', 'Cow Life', 'New calves born today', 'posted');
        INSERT INTO analytics_cache (content_row_id, platform, likes, comments, shares, reach, impressions)
        VALUES (1, 'instagram', 60, 10, 5, 500, 1200);
        INSERT INTO analytics_cache (content_row_id, platform, likes, comments, shares, reach, impressions)
        VALUES (1, 'facebook', 30, 5, 8, 300, 600);
        INSERT INTO analytics_cache (content_row_id, platform, likes, comments, shares, reach, impressions)
        VALUES (2, 'instagram', 25, 3, 2, 200, 400);
        INSERT INTO analytics_cache (content_row_id, platform, likes, comments, shares, reach, impressions)
        VALUES (3, 'instagram', 80, 15, 10, 700, 1500);
    """)
    conn.commit()
    conn.close()
    return db_path


class TestGetOverview:
    def test_returns_totals(self, engine_db):
        engine = AnalyticsEngine(str(engine_db))
        overview = engine.get_overview()
        assert "total_posts" in overview
        assert "total_engagement" in overview
        assert overview["total_posts"] >= 3

    def test_returns_avg_engagement(self, engine_db):
        engine = AnalyticsEngine(str(engine_db))
        overview = engine.get_overview()
        assert "avg_engagement" in overview
        assert overview["avg_engagement"] > 0


class TestGetPillarBreakdown:
    def test_returns_pillar_stats(self, engine_db):
        engine = AnalyticsEngine(str(engine_db))
        breakdown = engine.get_pillar_breakdown()
        assert len(breakdown) >= 2
        pillars = {b["pillar"] for b in breakdown}
        assert "Cow Life" in pillars
        assert "Community" in pillars

    def test_cow_life_has_higher_engagement(self, engine_db):
        engine = AnalyticsEngine(str(engine_db))
        breakdown = engine.get_pillar_breakdown()
        by_pillar = {b["pillar"]: b for b in breakdown}
        assert (
            by_pillar["Cow Life"]["total_engagement"] > by_pillar["Community"]["total_engagement"]
        )


class TestGetTopPosts:
    def test_returns_sorted_by_engagement(self, engine_db):
        engine = AnalyticsEngine(str(engine_db))
        top = engine.get_top_posts(limit=3)
        assert len(top) >= 2
        # First should have highest engagement
        assert top[0]["engagement"] >= top[1]["engagement"]

    def test_respects_limit(self, engine_db):
        engine = AnalyticsEngine(str(engine_db))
        top = engine.get_top_posts(limit=1)
        assert len(top) == 1
