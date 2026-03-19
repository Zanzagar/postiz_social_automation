"""Tests for BeautifulSoup web scraper (iskcongitanagari.org)."""

import sqlite3
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from content_engine.crawlers.web_scraper import WebScraper


SAMPLE_HTML = """
<html>
<head><title>ISKCON Gita Nagari</title></head>
<body>
<nav><a href="/about">About</a><a href="/cows">Cows</a></nav>
<main>
<h1>Welcome to Gita Nagari</h1>
<p>We are a spiritual farm community in Port Royal, PA.</p>
<p>Visit us for <a href="/sunday-feast">Sunday Feast</a> every week.</p>
</main>
<script>var x = 1;</script>
<footer>Copyright 2026</footer>
</body>
</html>
"""

ROBOTS_TXT = """
User-agent: *
Disallow: /admin/
Disallow: /private/
Allow: /
"""


class TestWebScraperInit:
    def test_default_fields(self):
        scraper = WebScraper("https://iskcongitanagari.org", "iskcon")
        assert scraper.base_url == "https://iskcongitanagari.org"
        assert scraper.site_name == "iskcon"
        assert scraper.rate_limit > 0

    def test_custom_rate_limit(self):
        scraper = WebScraper("https://example.com", "test", rate_limit=2.0)
        assert scraper.rate_limit == 2.0


class TestExtractContent:
    def test_extracts_title(self):
        scraper = WebScraper("https://iskcongitanagari.org", "iskcon")
        result = scraper.extract_content(SAMPLE_HTML)
        assert result["title"] == "ISKCON Gita Nagari"

    def test_extracts_body_text(self):
        scraper = WebScraper("https://iskcongitanagari.org", "iskcon")
        result = scraper.extract_content(SAMPLE_HTML)
        assert "spiritual farm community" in result["body_text"]

    def test_removes_scripts(self):
        scraper = WebScraper("https://iskcongitanagari.org", "iskcon")
        result = scraper.extract_content(SAMPLE_HTML)
        assert "var x" not in result["body_text"]

    def test_removes_nav_footer(self):
        scraper = WebScraper("https://iskcongitanagari.org", "iskcon")
        result = scraper.extract_content(SAMPLE_HTML)
        assert "Copyright 2026" not in result["body_text"]

    def test_empty_html(self):
        scraper = WebScraper("https://iskcongitanagari.org", "iskcon")
        result = scraper.extract_content("")
        assert result["title"] == ""
        assert result["body_text"] == ""


class TestDiscoverLinks:
    def test_finds_internal_links(self):
        scraper = WebScraper("https://iskcongitanagari.org", "iskcon")
        links = scraper.discover_links(SAMPLE_HTML, "https://iskcongitanagari.org/")
        assert "https://iskcongitanagari.org/about" in links
        assert "https://iskcongitanagari.org/cows" in links
        assert "https://iskcongitanagari.org/sunday-feast" in links

    def test_ignores_external_links(self):
        html = '<html><body><a href="https://google.com">G</a></body></html>'
        scraper = WebScraper("https://iskcongitanagari.org", "iskcon")
        links = scraper.discover_links(html, "https://iskcongitanagari.org/")
        assert len(links) == 0

    def test_deduplicates_links(self):
        html = '<html><body><a href="/x">X</a><a href="/x">X again</a></body></html>'
        scraper = WebScraper("https://iskcongitanagari.org", "iskcon")
        links = scraper.discover_links(html, "https://iskcongitanagari.org/")
        assert links.count("https://iskcongitanagari.org/x") == 1


class TestCanFetch:
    def test_allowed_path(self):
        scraper = WebScraper("https://iskcongitanagari.org", "iskcon")
        scraper.parse_robots(ROBOTS_TXT)
        assert scraper.can_fetch("https://iskcongitanagari.org/about") is True

    def test_disallowed_path(self):
        scraper = WebScraper("https://iskcongitanagari.org", "iskcon")
        scraper.parse_robots(ROBOTS_TXT)
        assert scraper.can_fetch("https://iskcongitanagari.org/admin/settings") is False


class TestContentHash:
    def test_hash_deterministic(self):
        scraper = WebScraper("https://iskcongitanagari.org", "iskcon")
        h1 = scraper.compute_content_hash("test")
        h2 = scraper.compute_content_hash("test")
        assert h1 == h2
        assert len(h1) == 64


@pytest.fixture
def scraper_db(tmp_path):
    """Temporary SQLite database with web_pages + web_knowledge tables."""
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


class TestScraperStorage:
    def test_store_page(self, scraper_db):
        scraper = WebScraper("https://iskcongitanagari.org", "iskcon")
        page_data = {
            "url": "https://iskcongitanagari.org/about",
            "title": "About",
            "body_text": "A spiritual farm community.",
            "content_hash": "abc",
            "site": "iskcon",
        }
        page_id = scraper.store_page_sync(str(scraper_db), page_data, pillar="Community")

        conn = sqlite3.connect(str(scraper_db))
        row = conn.execute("SELECT * FROM web_pages WHERE id = ?", (page_id,)).fetchone()
        conn.close()
        assert row is not None
        assert row[1] == "https://iskcongitanagari.org/about"

    def test_store_page_upserts(self, scraper_db):
        scraper = WebScraper("https://iskcongitanagari.org", "iskcon")
        page = {
            "url": "https://iskcongitanagari.org/x",
            "title": "X",
            "body_text": "v1",
            "content_hash": "h1",
            "site": "iskcon",
        }
        scraper.store_page_sync(str(scraper_db), page)
        page["body_text"] = "v2"
        page["content_hash"] = "h2"
        scraper.store_page_sync(str(scraper_db), page)

        conn = sqlite3.connect(str(scraper_db))
        count = conn.execute("SELECT COUNT(*) FROM web_pages").fetchone()[0]
        conn.close()
        assert count == 1
