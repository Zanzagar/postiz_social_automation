"""Tests for media upload, thumbnail generation, and AI tagging."""

import io
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine

from api.models import Base


@pytest.fixture(autouse=True)
def _clear_caches():
    from api.dependencies import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def _env_vars(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET", "test-secret-key-min-32-chars-long!!")
    monkeypatch.setenv("API_PASSWORD", "testpass")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("POSTIZ_API_KEY", "test-key")
    # Create tables in the test DB
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    engine.dispose()


@pytest.fixture
def client(_env_vars):
    from api.main import app

    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    resp = client.post("/api/auth/login", json={"password": "testpass"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _make_test_image(width=800, height=600, fmt="JPEG") -> io.BytesIO:
    """Create a test image in memory."""
    img = Image.new("RGB", (width, height), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    buf.seek(0)
    return buf


class TestMediaUpload:
    @patch("api.routes.media._generate_media_meta")
    @patch("api.routes.media._upload_to_postiz")
    def test_upload_creates_catalog_entry(
        self, mock_postiz, mock_meta, client, auth_headers, tmp_path
    ):
        mock_postiz.return_value = None  # Postiz upload optional
        mock_meta.return_value = {
            "alt_text": "An outdoor scene",
            "season": "summer",
            "tags": [{"tag": "outdoor", "confidence": 0.9}],
        }

        img = _make_test_image()
        resp = client.post(
            "/api/media/upload",
            files={"file": ("cow-photo.jpg", img, "image/jpeg")},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["filename"] == "cow-photo.jpg"
        assert data["mime_type"] == "image/jpeg"
        assert data["width"] == 800
        assert data["height"] == 600
        assert data["source"] == "upload"
        assert data["id"] is not None

    @patch("api.routes.media._generate_media_meta")
    @patch("api.routes.media._upload_to_postiz")
    def test_upload_generates_thumbnail(
        self, mock_postiz, mock_meta, client, auth_headers, tmp_path
    ):
        mock_postiz.return_value = None
        mock_meta.return_value = {"alt_text": "img", "season": None, "tags": []}

        img = _make_test_image(1920, 1080)
        resp = client.post(
            "/api/media/upload",
            files={"file": ("landscape.jpg", img, "image/jpeg")},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["thumbnail_path"] is not None
        # Verify thumbnail exists and is smaller
        thumb = Path(data["thumbnail_path"])
        assert thumb.exists()
        with Image.open(thumb) as t:
            assert t.width <= 200
            assert t.height <= 200

    @patch("api.routes.media._generate_media_meta")
    @patch("api.routes.media._upload_to_postiz")
    def test_upload_saves_tags(self, mock_postiz, mock_meta, client, auth_headers):
        mock_postiz.return_value = None
        mock_meta.return_value = {
            "alt_text": "Cows on a farm",
            "season": "spring",
            "tags": [
                {"tag": "cows", "confidence": 0.95},
                {"tag": "farm", "confidence": 0.8},
            ],
        }

        img = _make_test_image()
        resp = client.post(
            "/api/media/upload",
            files={"file": ("cows.jpg", img, "image/jpeg")},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["tags"]) == 2
        assert data["tags"][0]["tag"] == "cows"

    @patch("api.routes.media._generate_media_meta")
    @patch("api.routes.media._upload_to_postiz")
    def test_upload_persists_alt_text_and_season(
        self, mock_postiz, mock_meta, client, auth_headers
    ):
        mock_postiz.return_value = None
        mock_meta.return_value = {
            "alt_text": "A herd of cows grazing in a pasture.",
            "season": "fall",
            "tags": [{"tag": "cows", "confidence": 0.9}],
        }

        img = _make_test_image()
        resp = client.post(
            "/api/media/upload",
            files={"file": ("herd.jpg", img, "image/jpeg")},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["alt_text"] == "A herd of cows grazing in a pasture."
        assert data["season"] == "fall"

        # Persisted on the media row (visible via detail endpoint)
        detail = client.get(f"/api/media/{data['id']}", headers=auth_headers)
        assert detail.json()["media"]["alt_text"] == "A herd of cows grazing in a pasture."
        assert detail.json()["media"]["season"] == "fall"

    @patch("api.routes.media._generate_media_meta")
    @patch("api.routes.media._upload_to_postiz")
    def test_upload_ai_failure_non_fatal(self, mock_postiz, mock_meta, client, auth_headers):
        from api.routes.media import MediaMetaError

        mock_postiz.return_value = None
        mock_meta.side_effect = MediaMetaError("CLI unavailable")

        img = _make_test_image()
        resp = client.post(
            "/api/media/upload",
            files={"file": ("nofail.jpg", img, "image/jpeg")},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["alt_text"] is None
        assert data["season"] is None
        assert data["tags"] == []

    def test_upload_rejects_invalid_type(self, client, auth_headers):
        resp = client.post(
            "/api/media/upload",
            files={"file": ("doc.pdf", b"fake pdf content", "application/pdf")},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    @patch("api.routes.media._generate_media_meta")
    @patch("api.routes.media._upload_to_postiz")
    def test_postiz_failure_still_catalogs(self, mock_postiz, mock_meta, client, auth_headers):
        mock_postiz.side_effect = Exception("Postiz down")
        mock_meta.return_value = {"alt_text": "img", "season": None, "tags": []}

        img = _make_test_image()
        resp = client.post(
            "/api/media/upload",
            files={"file": ("test.jpg", img, "image/jpeg")},
            headers=auth_headers,
        )
        # Should still succeed — Postiz upload is optional
        assert resp.status_code == 201
        data = resp.json()
        assert data["postiz_media_id"] is None

    def test_upload_requires_auth(self, client):
        img = _make_test_image()
        resp = client.post(
            "/api/media/upload",
            files={"file": ("test.jpg", img, "image/jpeg")},
        )
        assert resp.status_code == 401


class TestMediaImportUrl:
    @patch("api.routes.media._generate_media_meta")
    @patch("api.routes.media._upload_to_postiz")
    @patch("api.routes.media._download_from_url")
    def test_import_url_creates_catalog(
        self, mock_download, mock_postiz, mock_meta, client, auth_headers
    ):
        img = _make_test_image()
        mock_download.return_value = (img.read(), "image/jpeg", "photo.jpg")
        mock_postiz.return_value = None
        mock_meta.return_value = {
            "alt_text": "A wide landscape",
            "season": "winter",
            "tags": [{"tag": "landscape", "confidence": 0.85}],
        }

        resp = client.post(
            "/api/media/import-url",
            json={"url": "https://example.com/photo.jpg"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["source"] == "import_url"
        assert data["original_url"] == "https://example.com/photo.jpg"
        assert data["alt_text"] == "A wide landscape"
        assert data["season"] == "winter"

    @patch("api.routes.media._download_from_url")
    def test_import_url_handles_download_failure(self, mock_download, client, auth_headers):
        mock_download.side_effect = Exception("404 Not Found")

        resp = client.post(
            "/api/media/import-url",
            json={"url": "https://example.com/missing.jpg"},
            headers=auth_headers,
        )
        assert resp.status_code == 400


class TestThumbnailGeneration:
    def test_thumbnail_maintains_aspect_ratio(self):
        from api.routes.media import _generate_thumbnail

        img = _make_test_image(1920, 1080)
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(img.read())
            src = Path(f.name)

        thumb_path = src.parent / f"thumb_{src.name}"
        _generate_thumbnail(src, thumb_path)

        with Image.open(thumb_path) as t:
            assert t.width <= 200
            assert t.height <= 200
            # 1920:1080 = 16:9, so width should be 200, height ~112
            assert t.width == 200
            assert 110 <= t.height <= 115

        src.unlink()
        thumb_path.unlink()

    def test_thumbnail_square_image(self):
        from api.routes.media import _generate_thumbnail

        img = _make_test_image(500, 500)
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(img.read())
            src = Path(f.name)

        thumb_path = src.parent / f"thumb_{src.name}"
        _generate_thumbnail(src, thumb_path)

        with Image.open(thumb_path) as t:
            assert t.width == 200
            assert t.height == 200

        src.unlink()
        thumb_path.unlink()
