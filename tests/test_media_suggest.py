"""Tests for AI media suggestion endpoint."""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from api.models import Base, ContentRow, MediaCatalog, MediaTag


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


def _seed_content_row(engine, **kw):
    with Session(engine) as s:
        row = ContentRow(
            raw_text=kw.get("raw_text", "Beautiful cows grazing on the farm"),
            pillar=kw.get("pillar", "farm_life"),
            status=kw.get("status", "draft"),
            platforms=json.dumps(kw.get("platforms", {"facebook": True})),
            captions=json.dumps(kw.get("captions", {})),
        )
        s.add(row)
        s.flush()
        row_id = row.id
        s.commit()
    return row_id


def _seed_media(engine, **kw):
    with Session(engine) as s:
        m = MediaCatalog(
            filename=kw.get("filename", "photo.jpg"),
            local_path=kw.get("local_path", "media/photo.jpg"),
            thumbnail_path=kw.get("thumbnail_path", "media/thumbnails/thumb.jpg"),
            mime_type="image/jpeg",
            file_size=50000,
            source=kw.get("source", "upload"),
            pillar=kw.get("pillar"),
            topic=kw.get("topic"),
            usage_count=kw.get("usage_count", 0),
            avg_engagement=kw.get("avg_engagement", 0.0),
            tags=json.dumps(kw.get("tag_list", [])),
        )
        s.add(m)
        s.flush()
        media_id = m.id
        s.commit()
    return media_id


def _seed_tags(engine, media_id, tags):
    with Session(engine) as s:
        for t in tags:
            s.add(
                MediaTag(
                    media_id=media_id,
                    tag=t,
                    confidence=0.9,
                    source="ai",
                )
            )
        s.commit()


class TestMediaSuggest:
    def test_returns_suggestions_format(self, client, auth_headers, db_engine):
        cr_id = _seed_content_row(db_engine)
        mid = _seed_media(db_engine, pillar="farm_life")
        _seed_tags(db_engine, mid, ["cows", "farm"])

        resp = client.get(
            f"/api/media/suggest?content_row_id={cr_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "suggestions" in data
        assert len(data["suggestions"]) >= 1
        s = data["suggestions"][0]
        assert "media_id" in s
        assert "thumbnail_path" in s
        assert "relevance_score" in s
        assert "match_reasons" in s

    def test_pillar_match_scores_higher(self, client, auth_headers, db_engine):
        cr_id = _seed_content_row(db_engine, pillar="farm_life")
        m_match = _seed_media(db_engine, pillar="farm_life", filename="match.jpg")
        m_no = _seed_media(db_engine, pillar="spiritual_education", filename="nomatch.jpg")

        resp = client.get(
            f"/api/media/suggest?content_row_id={cr_id}",
            headers=auth_headers,
        )
        data = resp.json()
        ids = [s["media_id"] for s in data["suggestions"]]
        # The pillar-matching media should come first
        assert ids.index(m_match) < ids.index(m_no)

    def test_tag_matching_in_reasons(self, client, auth_headers, db_engine):
        cr_id = _seed_content_row(db_engine, raw_text="Cows grazing in the farm pasture")
        mid = _seed_media(db_engine, filename="cows.jpg")
        _seed_tags(db_engine, mid, ["cows", "farm"])

        resp = client.get(
            f"/api/media/suggest?content_row_id={cr_id}",
            headers=auth_headers,
        )
        data = resp.json()
        reasons = data["suggestions"][0]["match_reasons"]
        tag_reasons = [r for r in reasons if r.startswith("tag:")]
        assert len(tag_reasons) >= 1

    def test_high_engagement_scores_higher(self, client, auth_headers, db_engine):
        cr_id = _seed_content_row(db_engine)
        m_high = _seed_media(db_engine, avg_engagement=0.9, filename="popular.jpg")
        m_low = _seed_media(db_engine, avg_engagement=0.1, filename="unpopular.jpg")

        resp = client.get(
            f"/api/media/suggest?content_row_id={cr_id}",
            headers=auth_headers,
        )
        data = resp.json()
        ids = [s["media_id"] for s in data["suggestions"]]
        assert ids.index(m_high) < ids.index(m_low)

    def test_empty_catalog_returns_empty(self, client, auth_headers, db_engine):
        cr_id = _seed_content_row(db_engine)
        resp = client.get(
            f"/api/media/suggest?content_row_id={cr_id}",
            headers=auth_headers,
        )
        data = resp.json()
        assert data["suggestions"] == []

    def test_returns_max_5(self, client, auth_headers, db_engine):
        cr_id = _seed_content_row(db_engine)
        for i in range(10):
            _seed_media(db_engine, filename=f"photo_{i}.jpg")

        resp = client.get(
            f"/api/media/suggest?content_row_id={cr_id}",
            headers=auth_headers,
        )
        data = resp.json()
        assert len(data["suggestions"]) <= 5

    def test_content_row_not_found(self, client, auth_headers):
        resp = client.get(
            "/api/media/suggest?content_row_id=9999",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_missing_content_row_id_param(self, client, auth_headers):
        resp = client.get("/api/media/suggest", headers=auth_headers)
        assert resp.status_code == 422
