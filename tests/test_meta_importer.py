"""Tests for Meta Graph API social history importer."""

import json
import re
import sqlite3
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from content_engine.crawlers.meta_importer import MetaGraphImporter


# --- Sample Graph API responses ---

SAMPLE_FB_POST = {
    "id": "293313989490_123456",
    "message": "Our cows enjoying the morning sun #GitaValley #CowProtection #AhimsaMilk",
    "created_time": "2026-01-15T10:30:00+0000",
    "attachments": {"data": [{"media": {"image": {"src": "https://example.com/cow.jpg"}}}]},
    "likes": {"summary": {"total_count": 45}},
    "comments": {"summary": {"total_count": 8}},
    "shares": {"count": 12},
}

SAMPLE_FB_POST_NO_SHARES = {
    "id": "293313989490_789",
    "message": "Sunday Feast this week! All welcome.",
    "created_time": "2026-02-01T08:00:00+0000",
    "likes": {"summary": {"total_count": 20}},
    "comments": {"summary": {"total_count": 3}},
}

SAMPLE_IG_POST = {
    "id": "17890012345",
    "caption": "Farm life at Gita Valley #FarmLife #Spiritual",
    "timestamp": "2026-01-20T14:00:00+0000",
    "media_url": "https://example.com/farm.jpg",
    "like_count": 60,
    "comments_count": 5,
}


class TestMetaImporterInit:
    def test_requires_access_token(self):
        importer = MetaGraphImporter(access_token="test_token")
        assert importer.access_token == "test_token"

    def test_default_graph_version(self):
        importer = MetaGraphImporter(access_token="tok")
        assert "v18.0" in importer.base_url or "v19.0" in importer.base_url

    def test_page_id(self):
        importer = MetaGraphImporter(access_token="tok", page_id="293313989490")
        assert importer.page_id == "293313989490"


class TestExtractHashtags:
    def test_extracts_hashtags(self):
        text = "Our cows #GitaValley #CowProtection"
        result = MetaGraphImporter.extract_hashtags(text)
        assert "GitaValley" in result
        assert "CowProtection" in result

    def test_empty_text(self):
        assert MetaGraphImporter.extract_hashtags("") == []
        assert MetaGraphImporter.extract_hashtags(None) == []

    def test_no_hashtags(self):
        assert MetaGraphImporter.extract_hashtags("Just a normal post") == []


class TestParseFacebookPost:
    def test_parse_with_all_fields(self):
        importer = MetaGraphImporter(access_token="tok")
        result = importer.parse_facebook_post(SAMPLE_FB_POST)
        assert result["platform"] == "facebook"
        assert result["external_id"] == "293313989490_123456"
        assert "cows enjoying" in result["post_text"]
        assert result["likes"] == 45
        assert result["comments"] == 8
        assert result["shares"] == 12
        assert "GitaValley" in result["hashtags"]
        assert isinstance(result["media_urls"], list)

    def test_parse_without_shares(self):
        importer = MetaGraphImporter(access_token="tok")
        result = importer.parse_facebook_post(SAMPLE_FB_POST_NO_SHARES)
        assert result["shares"] == 0

    def test_parse_extracts_media(self):
        importer = MetaGraphImporter(access_token="tok")
        result = importer.parse_facebook_post(SAMPLE_FB_POST)
        assert "https://example.com/cow.jpg" in result["media_urls"]


class TestParseInstagramPost:
    def test_parse_basic(self):
        importer = MetaGraphImporter(access_token="tok")
        result = importer.parse_instagram_post(SAMPLE_IG_POST)
        assert result["platform"] == "instagram"
        assert result["external_id"] == "17890012345"
        assert "Farm life" in result["post_text"]
        assert result["likes"] == 60
        assert result["comments"] == 5
        assert "FarmLife" in result["hashtags"]


@pytest.mark.asyncio
class TestFetchPosts:
    async def test_fetch_facebook_posts(self):
        importer = MetaGraphImporter(access_token="tok", page_id="293313989490")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [SAMPLE_FB_POST, SAMPLE_FB_POST_NO_SHARES],
            "paging": {},
        }

        with patch.object(importer, "_client") as mock_client:
            mock_client.get = AsyncMock(return_value=mock_resp)
            posts = await importer.fetch_facebook_posts()

        assert len(posts) == 2
        assert posts[0]["platform"] == "facebook"

    async def test_fetch_instagram_posts(self):
        importer = MetaGraphImporter(access_token="tok", instagram_account_id="12345")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [SAMPLE_IG_POST],
            "paging": {},
        }

        with patch.object(importer, "_client") as mock_client:
            mock_client.get = AsyncMock(return_value=mock_resp)
            posts = await importer.fetch_instagram_posts()

        assert len(posts) == 1
        assert posts[0]["platform"] == "instagram"

    async def test_fetch_instagram_skips_if_no_account_id(self):
        importer = MetaGraphImporter(access_token="tok")
        posts = await importer.fetch_instagram_posts()
        assert posts == []


# --- DB storage ---


@pytest.fixture
def social_db(tmp_path):
    """Temporary SQLite with social_history table."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
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
        )
    """)
    conn.commit()
    conn.close()
    return db_path


class TestStorePost:
    def test_store_inserts_new_post(self, social_db):
        importer = MetaGraphImporter(access_token="tok")
        post = importer.parse_facebook_post(SAMPLE_FB_POST)
        importer.store_post_sync(str(social_db), post)

        conn = sqlite3.connect(str(social_db))
        row = conn.execute(
            "SELECT * FROM social_history WHERE external_id = ?", ("293313989490_123456",)
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[1] == "facebook"

    def test_store_skips_duplicate(self, social_db):
        importer = MetaGraphImporter(access_token="tok")
        post = importer.parse_facebook_post(SAMPLE_FB_POST)
        importer.store_post_sync(str(social_db), post)
        importer.store_post_sync(str(social_db), post)  # duplicate

        conn = sqlite3.connect(str(social_db))
        count = conn.execute("SELECT COUNT(*) FROM social_history").fetchone()[0]
        conn.close()
        assert count == 1

    def test_store_multiple_posts(self, social_db):
        importer = MetaGraphImporter(access_token="tok")
        p1 = importer.parse_facebook_post(SAMPLE_FB_POST)
        p2 = importer.parse_facebook_post(SAMPLE_FB_POST_NO_SHARES)
        importer.store_post_sync(str(social_db), p1)
        importer.store_post_sync(str(social_db), p2)

        conn = sqlite3.connect(str(social_db))
        count = conn.execute("SELECT COUNT(*) FROM social_history").fetchone()[0]
        conn.close()
        assert count == 2
