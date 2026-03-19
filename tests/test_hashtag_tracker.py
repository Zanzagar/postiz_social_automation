"""Tests for hashtag performance tracking."""

import sqlite3

import pytest

from content_engine.analytics.hashtag_tracker import HashtagTracker


@pytest.fixture
def hashtag_db(tmp_path):
    """Temporary SQLite with hashtag_performance and social_history tables."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE hashtag_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hashtag TEXT NOT NULL,
            platform TEXT NOT NULL,
            times_used INTEGER DEFAULT 0,
            total_engagement INTEGER DEFAULT 0,
            avg_engagement REAL DEFAULT 0.0,
            trend TEXT DEFAULT 'stable',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(hashtag, platform)
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
        INSERT INTO social_history (platform, external_id, post_text, hashtags, likes, comments, shares)
        VALUES ('instagram', 'ig_1', 'Farm life', '["GitaValley","FarmLife"]', 60, 5, 2);
        INSERT INTO social_history (platform, external_id, post_text, hashtags, likes, comments, shares)
        VALUES ('instagram', 'ig_2', 'Cows!', '["GitaValley","CowProtection"]', 80, 10, 5);
        INSERT INTO social_history (platform, external_id, post_text, hashtags, likes, comments, shares)
        VALUES ('facebook', 'fb_1', 'Sunday', '["GitaValley"]', 30, 3, 8);
    """)
    conn.commit()
    conn.close()
    return db_path


class TestUpdatePerformance:
    def test_computes_from_social_history(self, hashtag_db):
        tracker = HashtagTracker(str(hashtag_db))
        tracker.update_performance()

        conn = sqlite3.connect(str(hashtag_db))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM hashtag_performance ORDER BY hashtag, platform"
        ).fetchall()
        conn.close()

        hashtags = {(r["hashtag"], r["platform"]): r for r in rows}
        # GitaValley on instagram: 2 uses (ig_1 + ig_2)
        assert ("GitaValley", "instagram") in hashtags
        gv_ig = hashtags[("GitaValley", "instagram")]
        assert gv_ig["times_used"] == 2

    def test_computes_avg_engagement(self, hashtag_db):
        tracker = HashtagTracker(str(hashtag_db))
        tracker.update_performance()

        conn = sqlite3.connect(str(hashtag_db))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM hashtag_performance WHERE hashtag = 'GitaValley' AND platform = 'instagram'"
        ).fetchone()
        conn.close()
        # ig_1: 60+5+2=67, ig_2: 80+10+5=95 -> total=162, avg=81
        assert row["total_engagement"] == 162
        assert abs(row["avg_engagement"] - 81.0) < 0.1


class TestGetTopHashtags:
    def test_returns_sorted_by_engagement(self, hashtag_db):
        tracker = HashtagTracker(str(hashtag_db))
        tracker.update_performance()
        top = tracker.get_top_hashtags(platform="instagram", limit=5)
        assert len(top) >= 2
        assert top[0]["total_engagement"] >= top[1]["total_engagement"]

    def test_filters_by_platform(self, hashtag_db):
        tracker = HashtagTracker(str(hashtag_db))
        tracker.update_performance()
        top = tracker.get_top_hashtags(platform="facebook")
        platforms = {t["platform"] for t in top}
        assert platforms == {"facebook"}


class TestSuggestHashtags:
    def test_suggest_returns_list(self, hashtag_db):
        tracker = HashtagTracker(str(hashtag_db))
        tracker.update_performance()
        suggestions = tracker.suggest_hashtags(platform="instagram", count=3)
        assert isinstance(suggestions, list)
        assert len(suggestions) <= 3
        assert all(isinstance(s, str) for s in suggestions)
