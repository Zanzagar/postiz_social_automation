"""Tests for WordPress REST API crawler (gitavalley.com)."""

import hashlib
import json
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
        assert "gitavalley.com" in crawler.base_url

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
    async def test_crawl_all_combines_posts_and_pages(self):
        crawler = WordPressCrawler()

        with patch.object(crawler, "fetch_all_items", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = [[SAMPLE_POST], [SAMPLE_PAGE]]
            pages = await crawler.crawl_all()

        assert len(pages) == 2
        assert mock_fetch.call_count == 2
        # Should call for both "posts" and "pages"
        call_args = [c.args[0] for c in mock_fetch.call_args_list]
        assert "posts" in call_args
        assert "pages" in call_args

    async def test_crawl_all_returns_parsed_dicts(self):
        crawler = WordPressCrawler()

        with patch.object(crawler, "fetch_all_items", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = [[SAMPLE_POST], []]
            pages = await crawler.crawl_all()

        assert len(pages) == 1
        page = pages[0]
        assert "url" in page
        assert "title" in page
        assert "body_text" in page
        assert "content_hash" in page
        assert "site" in page
