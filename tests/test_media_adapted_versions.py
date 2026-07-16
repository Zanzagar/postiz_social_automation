"""Tests for GET /api/media/{media_id}/adapted — list adapted versions.

Phase 3 PART B item 5.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from api.models import Base, MediaAdapted, MediaCatalog


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


def _seed_media(engine, **kw):
    with Session(engine) as s:
        m = MediaCatalog(
            filename=kw.get("filename", "photo.jpg"),
            local_path=kw.get("local_path", "media/photo.jpg"),
            mime_type=kw.get("mime_type", "image/jpeg"),
            file_size=1000,
            source="upload",
        )
        s.add(m)
        s.flush()
        media_id = m.id
        s.commit()
    return media_id


def _seed_adapted(engine, media_id, platform, fmt, **kw):
    with Session(engine) as s:
        rec = MediaAdapted(
            media_id=media_id,
            platform=platform,
            format=fmt,
            adapted_path=kw.get("adapted_path", f"media/adapted/{media_id}_{platform}_{fmt}.jpg"),
            width=kw.get("width", 1080),
            height=kw.get("height", 1080),
            has_text_overlay=kw.get("has_text_overlay", False),
        )
        s.add(rec)
        s.flush()
        rec_id = rec.id
        s.commit()
    return rec_id


class TestAdaptedVersionsList:
    def test_empty_list(self, client, auth_headers, db_engine):
        mid = _seed_media(db_engine)
        resp = client.get(f"/api/media/{mid}/adapted", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == {"adapted": []}

    def test_returns_versions_with_all_fields(self, client, auth_headers, db_engine):
        mid = _seed_media(db_engine)
        _seed_adapted(db_engine, mid, "instagram", "post", has_text_overlay=True)
        resp = client.get(f"/api/media/{mid}/adapted", headers=auth_headers)
        assert resp.status_code == 200
        adapted = resp.json()["adapted"]
        assert len(adapted) == 1
        v = adapted[0]
        assert v["platform"] == "instagram"
        assert v["format"] == "post"
        assert v["adapted_path"] == f"media/adapted/{mid}_instagram_post.jpg"
        assert v["width"] == 1080
        assert v["height"] == 1080
        assert v["has_text_overlay"] is True
        assert "id" in v
        assert "created_at" in v

    def test_ordered_by_platform_then_format(self, client, auth_headers, db_engine):
        mid = _seed_media(db_engine)
        _seed_adapted(db_engine, mid, "instagram", "story")
        _seed_adapted(db_engine, mid, "facebook", "post")
        _seed_adapted(db_engine, mid, "instagram", "post")
        resp = client.get(f"/api/media/{mid}/adapted", headers=auth_headers)
        adapted = resp.json()["adapted"]
        combos = [(a["platform"], a["format"]) for a in adapted]
        assert combos == [
            ("facebook", "post"),
            ("instagram", "post"),
            ("instagram", "story"),
        ]

    def test_only_returns_own_versions(self, client, auth_headers, db_engine):
        mid_a = _seed_media(db_engine)
        mid_b = _seed_media(db_engine, filename="other.jpg")
        _seed_adapted(db_engine, mid_a, "instagram", "post")
        _seed_adapted(db_engine, mid_b, "facebook", "post")
        resp = client.get(f"/api/media/{mid_a}/adapted", headers=auth_headers)
        adapted = resp.json()["adapted"]
        assert len(adapted) == 1
        assert adapted[0]["platform"] == "instagram"

    def test_media_not_found_404(self, client, auth_headers):
        resp = client.get("/api/media/9999/adapted", headers=auth_headers)
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Media not found"

    def test_requires_auth(self, client):
        resp = client.get("/api/media/1/adapted")
        assert resp.status_code == 401
