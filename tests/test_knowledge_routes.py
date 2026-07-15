"""Tests for knowledge base API endpoints."""

import sqlite3

import pytest
from httpx import ASGITransport, AsyncClient

from api.auth import get_current_user
from api.main import app
from api.routes.knowledge import get_db_path


@pytest.fixture
def knowledge_db(tmp_path):
    """Temporary SQLite with knowledge tables and sample data."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
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
        INSERT INTO web_pages (url, site, title, body_text, pillar, content_hash, last_crawled)
        VALUES ('https://gitavalley.com/about', 'gitavalley', 'About', 'A farm community.',
                'Community', 'abc', '2026-03-01T10:00:00');
        INSERT INTO web_pages (url, site, title, body_text, pillar, content_hash, last_crawled)
        VALUES ('https://iskcongitanagari.org/cows', 'iskcon', 'Cows', '85 cows on 430 acres.',
                'Cow Life', 'def', '2026-03-01T09:00:00');
        INSERT INTO web_knowledge (web_page_id, fact_type, content, pillar, keywords)
        VALUES (1, 'description', 'A spiritual farm community in PA.', 'Community',
                '["community","farm"]');
        INSERT INTO web_knowledge (web_page_id, fact_type, content, pillar, keywords)
        VALUES (2, 'program', 'Cow protection program with 85 cows.', 'Cow Life',
                '["cows","ahimsa"]');
        INSERT INTO social_history (platform, external_id, post_text, likes, comments, shares)
        VALUES ('facebook', 'fb_1', 'Our cows love the sunrise', 45, 8, 12);
        INSERT INTO social_history (platform, external_id, post_text, likes, comments, shares)
        VALUES ('instagram', 'ig_1', 'Farm life #GitaValley', 60, 5, 0);
    """)
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def knowledge_client(knowledge_db):
    """Override app dependencies for test database and auth."""
    app.dependency_overrides[get_current_user] = lambda: {"sub": "testuser"}
    app.dependency_overrides[get_db_path] = lambda: str(knowledge_db)
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestKnowledgeStatus:
    async def test_status_returns_source_stats(self, knowledge_client):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/knowledge/status")

        assert resp.status_code == 200
        data = resp.json()
        assert "sources" in data
        sources = {s["name"]: s for s in data["sources"]}
        assert "gitavalley" in sources
        assert "iskcon" in sources
        assert "facebook" in sources
        assert sources["gitavalley"]["page_count"] == 1
        assert sources["iskcon"]["page_count"] == 1
        assert sources["facebook"]["post_count"] == 1


@pytest.mark.asyncio
class TestKnowledgeStats:
    async def test_coverage_gap_count_is_total_not_list_length(
        self, knowledge_client, knowledge_db
    ):
        """coverage_gaps stays capped at 10, but coverage_gap_count is the true total."""
        conn = sqlite3.connect(str(knowledge_db))
        long_body = "x" * 300  # predicate requires length(body_text) > 200
        for i in range(12):
            conn.execute(
                "INSERT INTO web_pages (url, site, title, body_text) VALUES (?, ?, ?, ?)",
                (f"https://gitavalley.com/gap{i}", "gitavalley", f"Gap {i}", long_body),
            )
        conn.commit()
        conn.close()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/knowledge/stats")

        assert resp.status_code == 200
        data = resp.json()
        assert data["coverage_gap_count"] == 12
        assert len(data["coverage_gaps"]) == 10

    async def test_no_gaps_reports_zero(self, knowledge_client):
        """Seed pages are short (<200 chars) — no gap pages at all."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/knowledge/stats")

        assert resp.status_code == 200
        data = resp.json()
        assert data["coverage_gap_count"] == 0
        assert data["coverage_gaps"] == []
        assert data["total_pages"] == 2
        assert data["total_knowledge"] == 2


@pytest.mark.asyncio
class TestKnowledgeSearch:
    async def test_search_by_text(self, knowledge_client):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/knowledge/search", params={"q": "cow"})

        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert len(data["results"]) >= 1
        contents = [r["content"] for r in data["results"]]
        assert any("cow" in c.lower() for c in contents)

    async def test_search_by_pillar(self, knowledge_client):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/knowledge/search", params={"q": "", "pillar": "Community"}
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) >= 1

    async def test_search_empty_query_returns_all(self, knowledge_client):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/knowledge/search", params={"q": ""})

        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2  # both knowledge entries
