"""Tests for media adaptation endpoint — platform-specific image resizing."""


import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, select
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


def _create_test_image(tmp_path, width=1920, height=1080, filename="test.jpg"):
    """Create a real image file and DB record."""
    media_dir = tmp_path / "media"
    media_dir.mkdir(exist_ok=True)
    (media_dir / "adapted").mkdir(exist_ok=True)

    img = Image.new("RGB", (width, height), color=(100, 150, 200))
    file_path = media_dir / filename
    img.save(file_path, format="JPEG")
    return str(file_path)


def _seed_media(engine, local_path, **kw):
    with Session(engine) as s:
        m = MediaCatalog(
            filename=kw.get("filename", "test.jpg"),
            local_path=local_path,
            mime_type="image/jpeg",
            width=kw.get("width", 1920),
            height=kw.get("height", 1080),
            file_size=50000,
            source="upload",
        )
        s.add(m)
        s.flush()
        media_id = m.id
        s.commit()
    return media_id


class TestMediaAdapt:
    def test_adapt_instagram_post(self, client, auth_headers, db_engine, tmp_path):
        path = _create_test_image(tmp_path)
        mid = _seed_media(db_engine, path)

        resp = client.post(
            f"/api/media/{mid}/adapt",
            json={"platforms": ["instagram"], "formats": ["post"]},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["adapted"]) >= 1
        adapted = data["adapted"][0]
        assert adapted["platform"] == "instagram"
        assert adapted["format"] == "post"
        assert adapted["width"] == 1080
        assert adapted["height"] == 1080

    def test_adapt_facebook_post(self, client, auth_headers, db_engine, tmp_path):
        path = _create_test_image(tmp_path)
        mid = _seed_media(db_engine, path)

        resp = client.post(
            f"/api/media/{mid}/adapt",
            json={"platforms": ["facebook"], "formats": ["post"]},
            headers=auth_headers,
        )
        data = resp.json()
        fb = [a for a in data["adapted"] if a["platform"] == "facebook"]
        assert len(fb) == 1
        assert fb[0]["width"] == 1200
        assert fb[0]["height"] == 630

    def test_adapt_story_format(self, client, auth_headers, db_engine, tmp_path):
        path = _create_test_image(tmp_path)
        mid = _seed_media(db_engine, path)

        resp = client.post(
            f"/api/media/{mid}/adapt",
            json={"platforms": ["instagram"], "formats": ["story"]},
            headers=auth_headers,
        )
        data = resp.json()
        story = data["adapted"][0]
        assert story["width"] == 1080
        assert story["height"] == 1920

    def test_adapt_multiple_platforms(self, client, auth_headers, db_engine, tmp_path):
        path = _create_test_image(tmp_path)
        mid = _seed_media(db_engine, path)

        resp = client.post(
            f"/api/media/{mid}/adapt",
            json={
                "platforms": ["instagram", "facebook"],
                "formats": ["post"],
            },
            headers=auth_headers,
        )
        data = resp.json()
        platforms = {a["platform"] for a in data["adapted"]}
        assert "instagram" in platforms
        assert "facebook" in platforms

    def test_adapt_saves_to_db(self, client, auth_headers, db_engine, tmp_path):
        path = _create_test_image(tmp_path)
        mid = _seed_media(db_engine, path)

        client.post(
            f"/api/media/{mid}/adapt",
            json={"platforms": ["instagram"], "formats": ["post"]},
            headers=auth_headers,
        )

        with Session(db_engine) as s:
            records = (
                s.execute(select(MediaAdapted).where(MediaAdapted.media_id == mid)).scalars().all()
            )
            assert len(records) >= 1

    def test_adapt_creates_file(self, client, auth_headers, db_engine, tmp_path):
        path = _create_test_image(tmp_path)
        mid = _seed_media(db_engine, path)

        resp = client.post(
            f"/api/media/{mid}/adapt",
            json={"platforms": ["instagram"], "formats": ["post"]},
            headers=auth_headers,
        )
        adapted_path = resp.json()["adapted"][0]["adapted_path"]
        from pathlib import Path

        assert Path(adapted_path).exists()

    def test_adapt_not_found(self, client, auth_headers):
        resp = client.post(
            "/api/media/9999/adapt",
            json={"platforms": ["instagram"], "formats": ["post"]},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_adapt_missing_source_file(self, client, auth_headers, db_engine):
        mid = _seed_media(db_engine, "/nonexistent/file.jpg")
        resp = client.post(
            f"/api/media/{mid}/adapt",
            json={"platforms": ["instagram"], "formats": ["post"]},
            headers=auth_headers,
        )
        assert resp.status_code == 400


class TestSmartCrop:
    def test_landscape_to_square(self):
        from api.routes.media import _smart_crop

        img = Image.new("RGB", (1920, 1080))
        result = _smart_crop(img, 1080, 1080)
        assert result.size == (1080, 1080)

    def test_portrait_to_landscape(self):
        from api.routes.media import _smart_crop

        img = Image.new("RGB", (1080, 1920))
        result = _smart_crop(img, 1200, 630)
        assert result.size == (1200, 630)

    def test_same_aspect_ratio(self):
        from api.routes.media import _smart_crop

        img = Image.new("RGB", (1920, 1080))
        result = _smart_crop(img, 960, 540)
        assert result.size == (960, 540)
