"""Tests for PATCH /api/media/{media_id} and extended MediaItemResponse fields.

Phase 3 PART B items 2 + 3: alt_text / default_caption / season / original_url
on media items, and the metadata PATCH endpoint with clear-on-null semantics.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from api.models import Base, MediaCatalog


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
            original_url=kw.get("original_url"),
            mime_type=kw.get("mime_type", "image/jpeg"),
            file_size=kw.get("file_size", 1000),
            source=kw.get("source", "upload"),
            pillar=kw.get("pillar"),
            alt_text=kw.get("alt_text"),
            default_caption=kw.get("default_caption"),
            season=kw.get("season"),
        )
        s.add(m)
        s.flush()
        media_id = m.id
        s.commit()
    return media_id


class TestMediaUpdate:
    def test_patch_sets_alt_text(self, client, auth_headers, db_engine):
        mid = _seed_media(db_engine)
        resp = client.patch(
            f"/api/media/{mid}",
            json={"alt_text": "Cows grazing in a green pasture"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["alt_text"] == "Cows grazing in a green pasture"
        assert data["id"] == mid

    def test_patch_sets_all_fields(self, client, auth_headers, db_engine):
        mid = _seed_media(db_engine)
        resp = client.patch(
            f"/api/media/{mid}",
            json={
                "alt_text": "alt",
                "default_caption": "caption",
                "season": "summer",
                "pillar": "farm_life",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["alt_text"] == "alt"
        assert data["default_caption"] == "caption"
        assert data["season"] == "summer"
        assert data["pillar"] == "farm_life"

    def test_patch_null_clears_field(self, client, auth_headers, db_engine):
        mid = _seed_media(db_engine, alt_text="existing alt", season="winter")
        resp = client.patch(
            f"/api/media/{mid}",
            json={"alt_text": None},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["alt_text"] is None
        # season was absent from the patch → untouched
        assert data["season"] == "winter"

    def test_patch_absent_fields_untouched(self, client, auth_headers, db_engine):
        mid = _seed_media(db_engine, alt_text="keep me", pillar="events")
        resp = client.patch(
            f"/api/media/{mid}",
            json={"season": "spring"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["alt_text"] == "keep me"
        assert data["pillar"] == "events"
        assert data["season"] == "spring"

    def test_patch_season_case_insensitive_stored_lowercase(self, client, auth_headers, db_engine):
        mid = _seed_media(db_engine)
        resp = client.patch(
            f"/api/media/{mid}",
            json={"season": "Fall"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["season"] == "fall"
        with Session(db_engine) as s:
            row = s.execute(select(MediaCatalog).where(MediaCatalog.id == mid)).scalar_one()
            assert row.season == "fall"

    @pytest.mark.parametrize("season", ["spring", "SUMMER", "Fall", "winter", "ANY"])
    def test_patch_season_accepts_canonical_values(self, client, auth_headers, db_engine, season):
        mid = _seed_media(db_engine)
        resp = client.patch(
            f"/api/media/{mid}",
            json={"season": season},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["season"] == season.lower()

    def test_patch_season_invalid_422(self, client, auth_headers, db_engine):
        mid = _seed_media(db_engine)
        resp = client.patch(
            f"/api/media/{mid}",
            json={"season": "monsoon"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_patch_pillar_dynamic_string(self, client, auth_headers, db_engine):
        """Pillars are dynamic strings — any value must be accepted."""
        mid = _seed_media(db_engine)
        resp = client.patch(
            f"/api/media/{mid}",
            json={"pillar": "brand-new-pillar-2026"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["pillar"] == "brand-new-pillar-2026"

    def test_patch_not_found(self, client, auth_headers):
        resp = client.patch(
            "/api/media/9999",
            json={"alt_text": "x"},
            headers=auth_headers,
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Media not found"

    def test_patch_requires_auth(self, client):
        resp = client.patch("/api/media/1", json={"alt_text": "x"})
        assert resp.status_code == 401


class TestExtendedMediaItemFields:
    def test_browse_items_include_new_fields(self, client, auth_headers, db_engine):
        _seed_media(
            db_engine,
            alt_text="an alt",
            default_caption="a caption",
            season="fall",
            original_url="https://example.com/img.jpg",
        )
        resp = client.get("/api/media", headers=auth_headers)
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert item["alt_text"] == "an alt"
        assert item["default_caption"] == "a caption"
        assert item["season"] == "fall"
        assert item["original_url"] == "https://example.com/img.jpg"

    def test_browse_new_fields_default_null(self, client, auth_headers, db_engine):
        _seed_media(db_engine)
        resp = client.get("/api/media", headers=auth_headers)
        item = resp.json()["items"][0]
        assert item["alt_text"] is None
        assert item["default_caption"] is None
        assert item["season"] is None

    def test_detail_media_includes_new_fields(self, client, auth_headers, db_engine):
        mid = _seed_media(db_engine, alt_text="detail alt", season="any")
        resp = client.get(f"/api/media/{mid}", headers=auth_headers)
        assert resp.status_code == 200
        media = resp.json()["media"]
        assert media["alt_text"] == "detail alt"
        assert media["season"] == "any"
        assert "default_caption" in media
        assert "original_url" in media
