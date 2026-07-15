"""Tests for the _generate_media_meta helper and POST /api/media/{id}/generate-meta.

Phase 3 PART B item 7 — Claude CLI vision metadata (alt_text, season, tags).
"""

import io
import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from api.models import Base, MediaCatalog, MediaTag


@pytest.fixture(autouse=True)
def _clear_caches():
    import api.dependencies as deps
    from api.dependencies import get_settings

    get_settings.cache_clear()
    deps._engine = None
    deps._session_factory = None
    yield
    get_settings.cache_clear()
    deps._engine = None
    deps._session_factory = None


@pytest.fixture
def _env_vars(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET", "test-secret-key-min-32-chars-long!!")
    monkeypatch.setenv("API_PASSWORD", "testpass")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("POSTIZ_API_KEY", "test-key")
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    engine.dispose()


@pytest.fixture
def db_engine(_env_vars, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    yield engine
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


def _make_image_file(tmp_path, filename="src.jpg", width=800, height=600):
    img = Image.new("RGB", (width, height), color=(90, 120, 60))
    path = tmp_path / filename
    img.save(path, format="JPEG")
    return str(path)


def _seed_media(engine, **kw):
    with Session(engine) as s:
        m = MediaCatalog(
            filename=kw.get("filename", "photo.jpg"),
            local_path=kw.get("local_path", "media/photo.jpg"),
            mime_type=kw.get("mime_type", "image/jpeg"),
            file_size=1000,
            source=kw.get("source", "upload"),
            alt_text=kw.get("alt_text"),
            season=kw.get("season"),
        )
        s.add(m)
        s.flush()
        media_id = m.id
        s.commit()
    return media_id


_VALID_META = {
    "alt_text": "Two cows grazing in a fenced green pasture on a sunny day.",
    "season": "summer",
    "tags": [
        {"tag": "cows", "confidence": 0.95},
        {"tag": "farm", "confidence": 0.8},
    ],
}


def _cli_result(stdout, returncode=0):
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = ""
    return result


# ── Helper unit tests ────────────────────────────────────────────────────


class TestGenerateMediaMetaHelper:
    @patch("api.routes.media.subprocess.run")
    def test_parses_strict_json(self, mock_run):
        from api.routes.media import _generate_media_meta

        mock_run.return_value = _cli_result(json.dumps(_VALID_META))
        meta = _generate_media_meta("/tmp/x.jpg")
        assert meta["alt_text"] == _VALID_META["alt_text"]
        assert meta["season"] == "summer"
        assert meta["tags"] == _VALID_META["tags"]

    @patch("api.routes.media.subprocess.run")
    def test_strips_markdown_fences(self, mock_run):
        from api.routes.media import _generate_media_meta

        fenced = "```json\n" + json.dumps(_VALID_META) + "\n```"
        mock_run.return_value = _cli_result(fenced)
        meta = _generate_media_meta("/tmp/x.jpg")
        assert meta["alt_text"] == _VALID_META["alt_text"]

    @patch("api.routes.media.subprocess.run")
    def test_season_normalized_lowercase(self, mock_run):
        from api.routes.media import _generate_media_meta

        payload = dict(_VALID_META, season="Fall")
        mock_run.return_value = _cli_result(json.dumps(payload))
        assert _generate_media_meta("/tmp/x.jpg")["season"] == "fall"

    @patch("api.routes.media.subprocess.run")
    def test_invalid_season_coerced_to_none(self, mock_run):
        from api.routes.media import _generate_media_meta

        payload = dict(_VALID_META, season="monsoon")
        mock_run.return_value = _cli_result(json.dumps(payload))
        assert _generate_media_meta("/tmp/x.jpg")["season"] is None

    @patch("api.routes.media.subprocess.run")
    def test_invalid_json_raises(self, mock_run):
        from api.routes.media import MediaMetaError, _generate_media_meta

        mock_run.return_value = _cli_result("not json at all")
        with pytest.raises(MediaMetaError):
            _generate_media_meta("/tmp/x.jpg")

    @patch("api.routes.media.subprocess.run")
    def test_nonzero_returncode_raises(self, mock_run):
        from api.routes.media import MediaMetaError, _generate_media_meta

        mock_run.return_value = _cli_result("", returncode=1)
        with pytest.raises(MediaMetaError):
            _generate_media_meta("/tmp/x.jpg")

    @patch("api.routes.media.subprocess.run")
    def test_timeout_raises(self, mock_run):
        import subprocess

        from api.routes.media import MediaMetaError, _generate_media_meta

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=120)
        with pytest.raises(MediaMetaError):
            _generate_media_meta("/tmp/x.jpg")

    @patch("api.routes.media.subprocess.run")
    def test_missing_alt_text_raises(self, mock_run):
        from api.routes.media import MediaMetaError, _generate_media_meta

        payload = {"season": "summer", "tags": []}
        mock_run.return_value = _cli_result(json.dumps(payload))
        with pytest.raises(MediaMetaError):
            _generate_media_meta("/tmp/x.jpg")

    @patch("api.routes.media.subprocess.run")
    def test_classify_media_tags_backward_compat(self, mock_run):
        """src/content_engine imports _classify_media_tags — must keep working."""
        from api.routes.media import _classify_media_tags

        mock_run.return_value = _cli_result(json.dumps(_VALID_META))
        tags = _classify_media_tags("/tmp/x.jpg")
        assert tags == _VALID_META["tags"]

    @patch("api.routes.media.subprocess.run")
    def test_classify_media_tags_failure_returns_empty(self, mock_run):
        from api.routes.media import _classify_media_tags

        mock_run.return_value = _cli_result("garbage")
        assert _classify_media_tags("/tmp/x.jpg") == []


# ── Endpoint tests ───────────────────────────────────────────────────────


class TestGenerateMetaEndpoint:
    @patch("api.routes.media._generate_media_meta")
    def test_success_returns_meta(self, mock_meta, client, auth_headers, db_engine, tmp_path):
        path = _make_image_file(tmp_path)
        mid = _seed_media(db_engine, local_path=path)
        mock_meta.return_value = dict(_VALID_META)

        resp = client.post(f"/api/media/{mid}/generate-meta", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["alt_text"] == _VALID_META["alt_text"]
        assert data["season"] == "summer"
        assert data["suggested_tags"] == _VALID_META["tags"]

    @patch("api.routes.media._generate_media_meta")
    def test_persists_alt_text_and_season(
        self, mock_meta, client, auth_headers, db_engine, tmp_path
    ):
        path = _make_image_file(tmp_path)
        mid = _seed_media(db_engine, local_path=path, alt_text="old", season="winter")
        mock_meta.return_value = dict(_VALID_META)

        resp = client.post(f"/api/media/{mid}/generate-meta", headers=auth_headers)
        assert resp.status_code == 200
        with Session(db_engine) as s:
            row = s.execute(select(MediaCatalog).where(MediaCatalog.id == mid)).scalar_one()
            assert row.alt_text == _VALID_META["alt_text"]
            assert row.season == "summer"

    @patch("api.routes.media._generate_media_meta")
    def test_does_not_auto_add_tags(self, mock_meta, client, auth_headers, db_engine, tmp_path):
        path = _make_image_file(tmp_path)
        mid = _seed_media(db_engine, local_path=path)
        mock_meta.return_value = dict(_VALID_META)

        resp = client.post(f"/api/media/{mid}/generate-meta", headers=auth_headers)
        assert resp.status_code == 200
        with Session(db_engine) as s:
            tags = s.execute(select(MediaTag).where(MediaTag.media_id == mid)).scalars().all()
            assert tags == []

    def test_media_not_found_404(self, client, auth_headers):
        resp = client.post("/api/media/9999/generate-meta", headers=auth_headers)
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Media not found"

    def test_video_rejected_400(self, client, auth_headers, db_engine):
        mid = _seed_media(db_engine, mime_type="video/mp4", filename="clip.mp4")
        resp = client.post(f"/api/media/{mid}/generate-meta", headers=auth_headers)
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Only images supported"

    @patch("api.routes.media._generate_media_meta")
    def test_cli_failure_502(self, mock_meta, client, auth_headers, db_engine, tmp_path):
        from api.routes.media import MediaMetaError

        path = _make_image_file(tmp_path)
        mid = _seed_media(db_engine, local_path=path)
        mock_meta.side_effect = MediaMetaError("boom")

        resp = client.post(f"/api/media/{mid}/generate-meta", headers=auth_headers)
        assert resp.status_code == 502
        assert resp.json()["detail"] == "AI generation failed"

    def test_missing_source_file_502(self, client, auth_headers, db_engine):
        mid = _seed_media(db_engine, local_path="/nonexistent/gone.jpg")
        resp = client.post(f"/api/media/{mid}/generate-meta", headers=auth_headers)
        assert resp.status_code == 502
        assert resp.json()["detail"] == "AI generation failed"

    @patch("api.routes.media._generate_media_meta")
    @patch("api.routes.drive._download_drive_file")
    @patch("api.routes.drive.get_drive_service")
    def test_drive_media_supported(
        self, mock_service, mock_download, mock_meta, client, auth_headers, db_engine
    ):
        img = Image.new("RGB", (640, 480), color=(10, 20, 30))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        mock_service.return_value = MagicMock()
        mock_download.return_value = buf.getvalue()
        mock_meta.return_value = dict(_VALID_META)

        mid = _seed_media(db_engine, local_path="drive://abc123", source="drive")
        resp = client.post(f"/api/media/{mid}/generate-meta", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["alt_text"] == _VALID_META["alt_text"]

    def test_requires_auth(self, client):
        resp = client.post("/api/media/1/generate-meta")
        assert resp.status_code == 401
