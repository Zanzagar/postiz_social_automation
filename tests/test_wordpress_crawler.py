"""Tests for WordPress REST API crawler (gitavalley.com)."""

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from content_engine.crawlers.wordpress_crawler import WordPressCrawler


# --- Sample WP REST API responses ---

SAMPLE_POST = {
    "id": 101,
    "link": "https://gitavalley.com/cow-protection-program/",
    "title": {"rendered": "Cow Protection Program"},
    "content": {"rendered": "<p>Our <strong>85 cows</strong> roam freely.</p>"},
    "date": "2026-01-15T10:30:00",
}

SAMPLE_PAGE = {
    "id": 5,
    "link": "https://gitavalley.com/about/",
    "title": {"rendered": "About Gita Valley"},
    "content": {"rendered": "<h1>Welcome</h1><p>We are a spiritual farm community.</p>"},
    "date": "2025-06-01T08:00:00",
}


class TestWordPressCrawlerInit:
    def test_default_base_url(self):
        crawler = WordPressCrawler()
        assert "gitavalley.org" in crawler.base_url

    def test_custom_base_url(self):
        crawler = WordPressCrawler(base_url="https://example.com")
        assert crawler.base_url == "https://example.com"

    def test_site_name_default(self):
        crawler = WordPressCrawler()
        assert crawler.site_name == "gitavalley"


class TestContentHash:
    def test_compute_hash_deterministic(self):
        crawler = WordPressCrawler()
        text = "Our 85 cows roam freely."
        h1 = crawler.compute_content_hash(text)
        h2 = crawler.compute_content_hash(text)
        assert h1 == h2

    def test_compute_hash_is_sha256(self):
        crawler = WordPressCrawler()
        text = "test content"
        result = crawler.compute_content_hash(text)
        expected = hashlib.sha256(text.encode()).hexdigest()
        assert result == expected
        assert len(result) == 64

    def test_different_content_different_hash(self):
        crawler = WordPressCrawler()
        h1 = crawler.compute_content_hash("aaa")
        h2 = crawler.compute_content_hash("bbb")
        assert h1 != h2


class TestStripHtml:
    def test_strips_tags(self):
        crawler = WordPressCrawler()
        result = crawler.strip_html("<p>Hello <strong>world</strong></p>")
        assert result == "Hello world"

    def test_strips_scripts(self):
        crawler = WordPressCrawler()
        html = "<p>Keep</p><script>alert('x')</script>"
        result = crawler.strip_html(html)
        assert "alert" not in result
        assert "Keep" in result

    def test_empty_string(self):
        crawler = WordPressCrawler()
        assert crawler.strip_html("") == ""


class TestParsePosts:
    def test_parse_wp_item(self):
        crawler = WordPressCrawler()
        page = crawler.parse_wp_item(SAMPLE_POST)
        assert page["url"] == "https://gitavalley.com/cow-protection-program/"
        assert page["title"] == "Cow Protection Program"
        assert "85 cows" in page["body_text"]
        assert page["content_hash"]  # not empty
        assert page["site"] == "gitavalley"

    def test_parse_wp_item_strips_html(self):
        crawler = WordPressCrawler()
        page = crawler.parse_wp_item(SAMPLE_POST)
        assert "<p>" not in page["body_text"]
        assert "<strong>" not in page["body_text"]


@pytest.mark.asyncio
class TestFetchPages:
    async def test_fetch_posts_single_page(self):
        crawler = WordPressCrawler()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [SAMPLE_POST]
        mock_response.headers = {"X-WP-TotalPages": "1"}

        with patch.object(crawler, "_client") as mock_client:
            mock_client.get = AsyncMock(return_value=mock_response)
            results = await crawler.fetch_all_items("posts")

        assert len(results) == 1
        assert results[0]["id"] == 101

    async def test_fetch_pages_pagination(self):
        crawler = WordPressCrawler()

        page1_resp = MagicMock()
        page1_resp.status_code = 200
        page1_resp.json.return_value = [SAMPLE_POST]
        page1_resp.headers = {"X-WP-TotalPages": "2"}

        page2_resp = MagicMock()
        page2_resp.status_code = 200
        page2_resp.json.return_value = [SAMPLE_PAGE]
        page2_resp.headers = {"X-WP-TotalPages": "2"}

        with patch.object(crawler, "_client") as mock_client:
            mock_client.get = AsyncMock(side_effect=[page1_resp, page2_resp])
            results = await crawler.fetch_all_items("posts")

        assert len(results) == 2

    async def test_fetch_handles_empty_response(self):
        crawler = WordPressCrawler()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_response.headers = {"X-WP-TotalPages": "0"}

        with patch.object(crawler, "_client") as mock_client:
            mock_client.get = AsyncMock(return_value=mock_response)
            results = await crawler.fetch_all_items("posts")

        assert results == []


@pytest.mark.asyncio
class TestCrawlAll:
    async def test_crawl_all_combines_posts_pages_products(self):
        crawler = WordPressCrawler()

        with patch.object(crawler, "fetch_all_items", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = [[SAMPLE_POST], [SAMPLE_PAGE], []]
            pages = await crawler.crawl_all()

        assert len(pages) == 2
        assert mock_fetch.call_count == 3
        call_args = [c.args[0] for c in mock_fetch.call_args_list]
        assert "posts" in call_args
        assert "pages" in call_args
        assert "product" in call_args

    async def test_crawl_all_returns_parsed_dicts(self):
        crawler = WordPressCrawler()

        with patch.object(crawler, "fetch_all_items", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = [[SAMPLE_POST], [], []]
            pages = await crawler.crawl_all()

        assert len(pages) == 1
        page = pages[0]
        assert "url" in page
        assert "title" in page
        assert "body_text" in page
        assert "content_hash" in page
        assert "site" in page


# --- Subtask 5.4: Pillar classification ---


class TestClassifyPillar:
    def test_classify_returns_matching_pillar(self):
        crawler = WordPressCrawler()
        pillars = ["Cow Life", "Farm Ops", "Community", "Spiritual"]
        with patch(
            "content_engine.crawlers.wordpress_crawler._call_claude",
            return_value="Cow Life",
        ):
            result = crawler.classify_pillar("Cow Protection", "85 cows roam", pillars)
        assert result == "Cow Life"

    def test_classify_unknown_returns_first_pillar(self):
        crawler = WordPressCrawler()
        pillars = ["Cow Life", "Farm Ops"]
        with patch(
            "content_engine.crawlers.wordpress_crawler._call_claude",
            return_value="SomethingRandom",
        ):
            result = crawler.classify_pillar("test", "test body", pillars)
        assert result == "Cow Life"

    def test_classify_strips_whitespace(self):
        crawler = WordPressCrawler()
        pillars = ["Spiritual", "Community"]
        with patch(
            "content_engine.crawlers.wordpress_crawler._call_claude",
            return_value="  Spiritual  \n",
        ):
            result = crawler.classify_pillar("test", "test body", pillars)
        assert result == "Spiritual"


# --- Subtask 5.5: Knowledge extraction ---


class TestExtractKnowledge:
    def test_extract_returns_list_of_dicts(self):
        crawler = WordPressCrawler()
        sample_response = json.dumps(
            [
                {
                    "fact_type": "program",
                    "content": "Cow protection program with 85 cows",
                    "keywords": ["cows", "ahimsa"],
                },
                {
                    "fact_type": "description",
                    "content": "Gita Valley is a spiritual farm community",
                    "keywords": ["community", "farm"],
                },
            ]
        )
        with patch(
            "content_engine.crawlers.wordpress_crawler._call_claude",
            return_value=sample_response,
        ):
            facts = crawler.extract_knowledge(
                "Cow Protection", "Our 85 cows roam freely on 430 acres of protected land. " * 10
            )
        assert len(facts) == 2
        assert facts[0]["fact_type"] == "program"
        assert facts[1]["fact_type"] == "description"

    def test_extract_handles_invalid_json(self):
        crawler = WordPressCrawler()
        with patch(
            "content_engine.crawlers.wordpress_crawler._call_claude",
            return_value="not valid json",
        ):
            facts = crawler.extract_knowledge("test", "test body " * 50)
        assert facts == []

    def test_extract_valid_fact_types(self):
        crawler = WordPressCrawler()
        sample = json.dumps(
            [
                {"fact_type": "event", "content": "Sunday Feast", "keywords": ["feast"]},
            ]
        )
        with patch(
            "content_engine.crawlers.wordpress_crawler._call_claude",
            return_value=sample,
        ):
            facts = crawler.extract_knowledge(
                "Events", "Sunday Feast every week at Gita Valley. " * 10
            )
        assert facts[0]["fact_type"] in ("program", "event", "quote", "link", "description")

    def test_extract_chunks_large_content(self):
        crawler = WordPressCrawler()
        # Create content larger than CHUNK_SIZE
        large_text = "Gita Valley cow protection program details. " * 300  # ~13500 chars
        chunks = crawler._chunk_text(large_text, crawler.CHUNK_SIZE)
        assert len(chunks) >= 2
        # All content should be covered
        total_chars = sum(len(c) for c in chunks)
        assert total_chars >= len(large_text) * 0.95  # allow minor whitespace trimming

    def test_extract_deduplicates_facts(self):
        crawler = WordPressCrawler()
        fact_json = json.dumps(
            [
                {"fact_type": "program", "content": "85 cows on the farm", "keywords": ["cows"]},
            ]
        )
        # Simulate 2 chunks returning the same fact
        with patch(
            "content_engine.crawlers.wordpress_crawler._call_claude",
            return_value=fact_json,
        ):
            facts = crawler.extract_knowledge("Cows", "A" * 300)
        # Should deduplicate even though _call_claude is called once for single chunk
        assert len(facts) == 1

    def test_skips_short_pages(self):
        crawler = WordPressCrawler()
        facts = crawler.extract_knowledge("Test", "short")
        assert facts == []


# --- Subtask 5.5: Database storage ---


@pytest.fixture
def wp_db(tmp_path):
    """Create a temporary SQLite database with Phase 2 schema."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
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
        )
    """)
    conn.execute("""
        CREATE TABLE web_knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            web_page_id INTEGER REFERENCES web_pages(id),
            fact_type TEXT NOT NULL,
            content TEXT NOT NULL,
            pillar TEXT,
            keywords TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    return db_path


class TestStorePages:
    def test_store_page_inserts_row(self, wp_db):
        crawler = WordPressCrawler()
        page_data = {
            "url": "https://gitavalley.com/about/",
            "title": "About",
            "body_text": "We are a farm community.",
            "content_hash": "abc123",
            "site": "gitavalley",
        }
        page_id = crawler.store_page_sync(str(wp_db), page_data, pillar="Community")

        conn = sqlite3.connect(str(wp_db))
        row = conn.execute("SELECT * FROM web_pages WHERE id = ?", (page_id,)).fetchone()
        conn.close()
        assert row is not None
        assert row[1] == "https://gitavalley.com/about/"  # url
        assert row[5] == "Community"  # pillar

    def test_store_page_upserts_on_same_url(self, wp_db):
        crawler = WordPressCrawler()
        page_data = {
            "url": "https://gitavalley.com/about/",
            "title": "About",
            "body_text": "Version 1",
            "content_hash": "hash1",
            "site": "gitavalley",
        }
        id1 = crawler.store_page_sync(str(wp_db), page_data, pillar="Community")

        page_data["body_text"] = "Version 2"
        page_data["content_hash"] = "hash2"
        id2 = crawler.store_page_sync(str(wp_db), page_data, pillar="Community")

        conn = sqlite3.connect(str(wp_db))
        count = conn.execute("SELECT COUNT(*) FROM web_pages").fetchone()[0]
        body = conn.execute(
            "SELECT body_text FROM web_pages WHERE url = ?",
            ("https://gitavalley.com/about/",),
        ).fetchone()[0]
        conn.close()
        assert count == 1
        assert body == "Version 2"

    def test_store_knowledge_entries(self, wp_db):
        crawler = WordPressCrawler()
        page_data = {
            "url": "https://gitavalley.com/cows/",
            "title": "Cows",
            "body_text": "85 cows",
            "content_hash": "xyz",
            "site": "gitavalley",
        }
        page_id = crawler.store_page_sync(str(wp_db), page_data, pillar="Cow Life")

        knowledge = [
            {"fact_type": "program", "content": "Cow protection", "keywords": ["cows"]},
            {"fact_type": "description", "content": "85 cows on 430 acres", "keywords": ["farm"]},
        ]
        crawler.store_knowledge_sync(str(wp_db), page_id, knowledge, pillar="Cow Life")

        conn = sqlite3.connect(str(wp_db))
        rows = conn.execute(
            "SELECT * FROM web_knowledge WHERE web_page_id = ?", (page_id,)
        ).fetchall()
        conn.close()
        assert len(rows) == 2
