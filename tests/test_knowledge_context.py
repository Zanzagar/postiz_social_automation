"""Tests for knowledge context injection into caption generation."""

import json
import sqlite3

import pytest

from content_engine.crawlers.knowledge_context import get_knowledge_context


@pytest.fixture
def context_db(tmp_path):
    """Temporary SQLite with sample knowledge and social history."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE web_knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            web_page_id INTEGER,
            fact_type TEXT NOT NULL,
            content TEXT NOT NULL,
            topic TEXT,
            pillar TEXT,
            keywords TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
        INSERT INTO web_knowledge (fact_type, content, pillar, keywords)
        VALUES ('program', '85 cows on 430 acres of protected land.', 'Cow Life', '["cows","ahimsa"]');
        INSERT INTO web_knowledge (fact_type, content, pillar, keywords)
        VALUES ('event', 'Sunday Feast every week at 4pm.', 'Community', '["feast","events"]');
        INSERT INTO web_knowledge (fact_type, content, pillar, keywords)
        VALUES ('description', 'Gita Valley is in Port Royal, PA.', 'Community', '["location"]');
        INSERT INTO social_history (platform, external_id, post_text, likes, comments, shares, pillar)
        VALUES ('facebook', 'fb_1', 'Our cows enjoying the morning sun #CowProtection', 45, 8, 12, 'Cow Life');
        INSERT INTO social_history (platform, external_id, post_text, likes, comments, shares, pillar)
        VALUES ('instagram', 'ig_1', 'Farm life #GitaValley', 60, 5, 0, 'Farm Ops');
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
        INSERT INTO hashtag_performance (hashtag, platform, times_used, total_engagement, avg_engagement)
        VALUES ('GitaValley', 'instagram', 5, 500, 100.0);
        INSERT INTO hashtag_performance (hashtag, platform, times_used, total_engagement, avg_engagement)
        VALUES ('CowProtection', 'instagram', 3, 300, 100.0);
    """)
    conn.commit()
    conn.close()
    return db_path


class TestGetKnowledgeContext:
    def test_returns_string(self, context_db):
        result = get_knowledge_context(str(context_db), pillar="Cow Life")
        assert isinstance(result, str)

    def test_includes_relevant_facts(self, context_db):
        result = get_knowledge_context(str(context_db), pillar="Cow Life")
        assert "85 cows" in result

    def test_no_social_examples_in_knowledge_context(self, context_db):
        """Social history voice examples moved to voice-profile.json."""
        result = get_knowledge_context(str(context_db), pillar="Cow Life")
        assert "VOICE REFERENCE" not in result

    def test_filters_by_pillar(self, context_db):
        result = get_knowledge_context(str(context_db), pillar="Cow Life")
        # Should NOT include Community-specific facts when asking for Cow Life
        assert "Sunday Feast" not in result

    def test_no_pillar_returns_all(self, context_db):
        result = get_knowledge_context(str(context_db))
        assert "85 cows" in result
        assert "Sunday Feast" in result

    def test_missing_db_returns_empty(self, tmp_path):
        result = get_knowledge_context(str(tmp_path / "missing.db"))
        assert result == ""

    def test_respects_token_limit(self, context_db):
        result = get_knowledge_context(str(context_db), max_chars=50)
        assert len(result) <= 200  # some overhead for headers

    def test_includes_hashtag_suggestions(self, context_db):
        result = get_knowledge_context(str(context_db))
        assert "SUGGESTED HASHTAGS" in result
        assert "#GitaValley" in result
