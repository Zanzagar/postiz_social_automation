"""Tests for media attach/detach endpoints on content rows."""

import json

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from api.models import Base, ContentRow, MediaCatalog


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
            raw_text=kw.get("raw_text", "Test post"),
            status="draft",
            platforms=json.dumps({"facebook": True}),
            captions=json.dumps({}),
            media_catalog_ids=kw.get("media_catalog_ids"),
        )
        s.add(row)
        s.flush()
        row_id = row.id
        s.commit()
    return row_id


class TestAttachMedia:
    def test_attach_media(self, client, auth_headers, db_engine):
        cr_id = _seed_content_row(db_engine)
        resp = client.put(
            f"/api/content/{cr_id}/attach-media?media_id=42",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert 42 in resp.json()["media_catalog_ids"]

    def test_attach_idempotent(self, client, auth_headers, db_engine):
        cr_id = _seed_content_row(db_engine, media_catalog_ids=json.dumps([42]))
        resp = client.put(
            f"/api/content/{cr_id}/attach-media?media_id=42",
            headers=auth_headers,
        )
        assert resp.json()["media_catalog_ids"].count(42) == 1

    def test_attach_multiple(self, client, auth_headers, db_engine):
        cr_id = _seed_content_row(db_engine)
        client.put(
            f"/api/content/{cr_id}/attach-media?media_id=1",
            headers=auth_headers,
        )
        resp = client.put(
            f"/api/content/{cr_id}/attach-media?media_id=2",
            headers=auth_headers,
        )
        ids = resp.json()["media_catalog_ids"]
        assert 1 in ids
        assert 2 in ids

    def test_attach_not_found(self, client, auth_headers):
        resp = client.put(
            "/api/content/9999/attach-media?media_id=1",
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestDetachMedia:
    def test_detach_media(self, client, auth_headers, db_engine):
        cr_id = _seed_content_row(db_engine, media_catalog_ids=json.dumps([42, 99]))
        resp = client.put(
            f"/api/content/{cr_id}/detach-media?media_id=42",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert 42 not in resp.json()["media_catalog_ids"]
        assert 99 in resp.json()["media_catalog_ids"]

    def test_detach_last_clears(self, client, auth_headers, db_engine):
        cr_id = _seed_content_row(db_engine, media_catalog_ids=json.dumps([42]))
        resp = client.put(
            f"/api/content/{cr_id}/detach-media?media_id=42",
            headers=auth_headers,
        )
        assert resp.json()["media_catalog_ids"] == []

    def test_detach_nonexistent_no_error(self, client, auth_headers, db_engine):
        cr_id = _seed_content_row(db_engine)
        resp = client.put(
            f"/api/content/{cr_id}/detach-media?media_id=999",
            headers=auth_headers,
        )
        assert resp.status_code == 200


class TestAutoAdapt:
    def test_attach_triggers_adaptation(self, client, auth_headers, db_engine, tmp_path):
        """When media is attached, adapted versions should be generated."""
        # Create a real image + media record
        media_dir = tmp_path / "media"
        media_dir.mkdir(exist_ok=True)
        (media_dir / "adapted").mkdir(exist_ok=True)
        img = Image.new("RGB", (1920, 1080), color=(100, 150, 200))
        file_path = media_dir / "test.jpg"
        img.save(file_path, format="JPEG")

        with Session(db_engine) as s:
            m = MediaCatalog(
                filename="test.jpg",
                local_path=str(file_path),
                mime_type="image/jpeg",
                width=1920,
                height=1080,
                file_size=50000,
                source="upload",
            )
            s.add(m)
            s.flush()
            media_id = m.id
            s.commit()

        # Create content row with facebook platform
        cr_id = _seed_content_row(db_engine)

        # Attach media
        resp = client.put(
            f"/api/content/{cr_id}/attach-media?media_id={media_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert media_id in resp.json()["media_catalog_ids"]

        # Check adapted versions were created
        data = resp.json()
        assert "adapted_count" in data
        assert data["adapted_count"] >= 1

    def test_attach_skips_adapt_if_no_image(self, client, auth_headers, db_engine):
        """If the media file doesn't exist, attach still works but no adapt."""
        with Session(db_engine) as s:
            m = MediaCatalog(
                filename="missing.jpg",
                local_path="/nonexistent/missing.jpg",
                mime_type="image/jpeg",
                file_size=50000,
                source="upload",
            )
            s.add(m)
            s.flush()
            media_id = m.id
            s.commit()

        cr_id = _seed_content_row(db_engine)
        resp = client.put(
            f"/api/content/{cr_id}/attach-media?media_id={media_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["adapted_count"] == 0
