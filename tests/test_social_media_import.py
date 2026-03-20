"""Tests for social history media import script."""

from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from api.models import Base, MediaCatalog, SocialHistory


@pytest.fixture
def db_engine(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    monkeypatch.setenv("META_PAGE_ACCESS_TOKEN", "test-token")
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    return engine


def _seed_social_post(engine, external_id="12345_67890", **kw):
    with Session(engine) as s:
        post = SocialHistory(
            platform="facebook",
            external_id=external_id,
            post_text=kw.get("post_text", "Beautiful day at Gita Valley"),
            likes=kw.get("likes", 50),
            comments=kw.get("comments", 10),
            shares=kw.get("shares", 5),
            reach=kw.get("reach", 500),
            pillar=kw.get("pillar", "farm_life"),
        )
        s.add(post)
        s.flush()
        post_id = post.id
        s.commit()
    return post_id


class TestFetchAttachments:
    @patch("content_engine.scripts.import_social_media.httpx.get")
    def test_extracts_image_urls(self, mock_get):
        from content_engine.scripts.import_social_media import (
            fetch_post_attachments,
        )

        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status = lambda: None
        mock_get.return_value.json.return_value = {
            "attachments": {
                "data": [
                    {
                        "media": {
                            "image": {
                                "src": "https://fb.com/photo1.jpg",
                            }
                        }
                    }
                ]
            }
        }

        urls = fetch_post_attachments("12345", "token")
        assert len(urls) == 1
        assert urls[0] == "https://fb.com/photo1.jpg"

    @patch("content_engine.scripts.import_social_media.httpx.get")
    def test_handles_no_attachments(self, mock_get):
        from content_engine.scripts.import_social_media import (
            fetch_post_attachments,
        )

        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status = lambda: None
        mock_get.return_value.json.return_value = {}

        urls = fetch_post_attachments("12345", "token")
        assert urls == []

    @patch("content_engine.scripts.import_social_media.httpx.get")
    def test_handles_api_error(self, mock_get):
        from content_engine.scripts.import_social_media import (
            fetch_post_attachments,
        )

        mock_get.side_effect = Exception("API error")
        urls = fetch_post_attachments("12345", "token")
        assert urls == []


class TestMainImport:
    @patch("content_engine.scripts.import_social_media._classify_media_tags")
    @patch("content_engine.scripts.import_social_media.download_image")
    @patch("content_engine.scripts.import_social_media.fetch_post_attachments")
    def test_imports_media_from_posts(
        self, mock_fetch, mock_download, mock_tags, db_engine, tmp_path
    ):
        import io

        from PIL import Image as PILImage

        from content_engine.scripts.import_social_media import main

        _seed_social_post(db_engine)

        mock_fetch.return_value = ["https://fb.com/photo.jpg"]
        img = PILImage.new("RGB", (800, 600))
        buf = io.BytesIO()
        img.save(buf, "JPEG")
        mock_download.return_value = buf.getvalue()
        mock_tags.return_value = [{"tag": "farm", "confidence": 0.9}]

        main()

        with Session(db_engine) as s:
            media = (
                s.execute(select(MediaCatalog).where(MediaCatalog.source == "social_import"))
                .scalars()
                .all()
            )
            assert len(media) == 1
            assert media[0].pillar == "farm_life"

    @patch("content_engine.scripts.import_social_media._classify_media_tags")
    @patch("content_engine.scripts.import_social_media.download_image")
    @patch("content_engine.scripts.import_social_media.fetch_post_attachments")
    def test_skips_already_imported(self, mock_fetch, mock_download, mock_tags, db_engine):
        from content_engine.scripts.import_social_media import main

        post_id = _seed_social_post(db_engine)

        # Pre-seed an existing import
        with Session(db_engine) as s:
            s.add(
                MediaCatalog(
                    filename="existing.jpg",
                    local_path="media/existing.jpg",
                    original_url=f"social_history:{post_id}",
                    mime_type="image/jpeg",
                    file_size=100,
                    source="social_import",
                )
            )
            s.commit()

        main()

        # fetch_post_attachments should not be called for skipped posts
        mock_fetch.assert_not_called()
