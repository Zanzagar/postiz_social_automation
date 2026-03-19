"""End-to-end integration tests for Phase 2 Intelligence Layer.

Tests the full pipeline: crawl → store → search → inject into generation.
"""

import json
import sqlite3

import pytest
from httpx import ASGITransport, AsyncClient

from api.auth import get_current_user
from api.main import app
from api.routes.analytics import get_db_path as analytics_db_path
from api.routes.knowledge import get_db_path as knowledge_db_path


@pytest.fixture
def phase2_db(tmp_path):
    """Full Phase 2 schema with sample data simulating a crawl + import cycle."""
    db_path = tmp_path / "phase2.db"
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
        CREATE TABLE web_pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            site TEXT NOT NULL,
            title TEXT,
            body_text TEXT,
            pillar TEXT,
            content_hash TEXT,
            last_crawled DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE web_knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            web_page_id INTEGER REFERENCES web_pages(id),
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

        -- Seed data: simulate completed crawl
        INSERT INTO web_pages (url, site, title, body_text, pillar, content_hash, last_crawled)
        VALUES ('https://gitavalley.com/about', 'gitavalley', 'About Gita Valley',
                'Gita Valley is a 430-acre eco-farm and cow sanctuary.', 'Community', 'hash1', '2026-03-15');
        INSERT INTO web_pages (url, site, title, body_text, pillar, content_hash, last_crawled)
        VALUES ('https://gitavalley.com/cows', 'gitavalley', 'Our Cows',
                '85 cows on 430 acres of protected land.', 'Cow Life', 'hash2', '2026-03-15');

        INSERT INTO web_knowledge (web_page_id, fact_type, content, pillar, keywords)
        VALUES (1, 'description', '430-acre regenerative eco-farm in Port Royal, PA.', 'Community', '["farm","eco"]');
        INSERT INTO web_knowledge (web_page_id, fact_type, content, pillar, keywords)
        VALUES (2, 'program', 'Cow protection program: 85 cows, never separated from calves.', 'Cow Life', '["cows","ahimsa"]');
        INSERT INTO web_knowledge (web_page_id, fact_type, content, pillar, keywords)
        VALUES (2, 'quote', 'Only USDA Certified Slaughter-Free Dairy Farm in North America.', 'Cow Life', '["dairy","USDA"]');

        -- Seed data: simulate social import
        INSERT INTO social_history (platform, external_id, post_text, hashtags, likes, comments, shares, pillar)
        VALUES ('facebook', 'fb_1', 'Our cows enjoying the morning sun', '["GitaValley","CowProtection"]', 45, 8, 12, 'Cow Life');
        INSERT INTO social_history (platform, external_id, post_text, hashtags, likes, comments, shares, pillar)
        VALUES ('instagram', 'ig_1', 'Farm life at Gita Valley', '["GitaValley","FarmLife"]', 80, 12, 3, 'Farm Ops');

        -- Seed data: simulate analytics
        INSERT INTO content_rows (id, date, content_pillar, raw_text, status)
        VALUES (1, '2026-03-01', 'Cow Life', 'Morning sun on the farm', 'posted');
        INSERT INTO analytics_cache (content_row_id, platform, likes, comments, shares, reach, impressions)
        VALUES (1, 'instagram', 80, 12, 5, 600, 1400);

        -- Seed data: hashtag performance
        INSERT INTO hashtag_performance (hashtag, platform, times_used, total_engagement, avg_engagement)
        VALUES ('GitaValley', 'instagram', 10, 1000, 100.0);
        INSERT INTO hashtag_performance (hashtag, platform, times_used, total_engagement, avg_engagement)
        VALUES ('CowProtection', 'facebook', 5, 400, 80.0);
    """)
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def phase2_client(phase2_db):
    """Override all Phase 2 dependencies for testing."""
    db_str = str(phase2_db)
    app.dependency_overrides[get_current_user] = lambda: {"sub": "testuser"}
    app.dependency_overrides[knowledge_db_path] = lambda: db_str
    app.dependency_overrides[analytics_db_path] = lambda: db_str
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestKnowledgePipeline:
    """Tests the crawl → store → search pipeline."""

    async def test_knowledge_status_after_crawl(self, phase2_client):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/knowledge/status")

        assert resp.status_code == 200
        data = resp.json()
        sources = {s["name"]: s for s in data["sources"]}
        assert sources["gitavalley"]["page_count"] == 2
        assert sources["facebook"]["post_count"] == 1
        assert sources["instagram"]["post_count"] == 1
        assert data["knowledge_entries"] == 3

    async def test_knowledge_search_finds_cow_facts(self, phase2_client):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/knowledge/search", params={"q": "cow"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 1
        contents = [r["content"] for r in data["results"]]
        assert any("cow" in c.lower() for c in contents)

    async def test_knowledge_search_filters_by_pillar(self, phase2_client):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/knowledge/search", params={"q": "", "pillar": "Community"}
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 1
        assert all(r["pillar"] == "Community" for r in data["results"])


@pytest.mark.asyncio
class TestAnalyticsPipeline:
    """Tests analytics data flow from cache to API."""

    async def test_analytics_overview(self, phase2_client):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/analytics/overview")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_posts"] >= 1
        assert data["total_engagement"] > 0
        assert data["avg_engagement"] > 0

    async def test_pillar_breakdown(self, phase2_client):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/analytics/pillars")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["pillars"]) >= 1
        assert data["pillars"][0]["pillar"] == "Cow Life"

    async def test_top_posts(self, phase2_client):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/analytics/top-posts?limit=5")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["posts"]) >= 1
        assert data["posts"][0]["engagement"] > 0


class TestKnowledgeInjection:
    """Tests that knowledge context is built correctly for prompts."""

    def test_knowledge_context_includes_facts_and_hashtags(self, phase2_db):
        from content_engine.crawlers.knowledge_context import get_knowledge_context

        ctx = get_knowledge_context(str(phase2_db), pillar="Cow Life")
        assert "cow protection" in ctx.lower() or "85 cows" in ctx.lower()
        assert "SUGGESTED HASHTAGS" in ctx
        assert "#CowProtection" in ctx

    def test_knowledge_context_includes_social_examples(self, phase2_db):
        from content_engine.crawlers.knowledge_context import get_knowledge_context

        ctx = get_knowledge_context(str(phase2_db), pillar="Cow Life")
        assert "morning sun" in ctx.lower()

    def test_full_context_for_generation(self, phase2_db):
        """Verify the generator can build a prompt with knowledge context."""
        from content_engine.generator import CaptionGenerator

        gen = CaptionGenerator(db_path=str(phase2_db))
        ctx = gen._get_knowledge_context("Cow Life")
        assert len(ctx) > 0
        assert "KNOWLEDGE BASE FACTS" in ctx
