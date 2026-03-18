"""Tests for auto-publish configuration API (Task #7).

Tests cover:
- GET /api/settings/publish — list all publish configs
- PUT /api/settings/publish — upsert platform configs
- Config defaults, pillar overrides
"""

import asyncio

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.models import Base


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    from api.dependencies import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def _env_vars(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-key-min-32-chars-long!!")
    monkeypatch.setenv("API_PASSWORD", "testpass")
    monkeypatch.setenv("POSTIZ_API_KEY", "test-postiz-key")
    monkeypatch.setenv("SPREADSHEET_ID", "test-spreadsheet-id")
    monkeypatch.setenv("GOOGLE_SHEETS_CREDENTIALS", "/tmp/test-creds.json")
    monkeypatch.setenv("DATABASE_PATH", ":memory:")


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def repo(db_session):
    from api.repositories.content import ContentRepository

    return ContentRepository(db_session)


@pytest.fixture
def client(_env_vars, db_session, repo):
    from api.auth import get_current_user
    from api.dependencies import get_content_repo, get_db
    from api.main import app

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_content_repo] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: {"sub": "testuser"}

    yield TestClient(app)
    app.dependency_overrides.clear()


class TestGetPublishConfig:
    def test_empty_config(self, client):
        resp = client.get("/api/settings/publish")
        assert resp.status_code == 200
        data = resp.json()
        assert data["platforms"] == []

    def test_returns_saved_configs(self, client, repo):
        asyncio.get_event_loop().run_until_complete(
            repo.upsert_publish_config(
                "instagram",
                {"enabled": True, "delay_hours": 4},
            )
        )
        resp = client.get("/api/settings/publish")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["platforms"]) == 1
        assert data["platforms"][0]["platform"] == "instagram"
        assert data["platforms"][0]["enabled"] is True
        assert data["platforms"][0]["delay_hours"] == 4


class TestUpdatePublishConfig:
    def test_create_new_config(self, client):
        resp = client.put(
            "/api/settings/publish",
            json={
                "platforms": [
                    {"platform": "instagram", "enabled": True, "delay_hours": 2},
                    {"platform": "facebook", "enabled": True, "delay_hours": 4},
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["platforms"]) == 2
        ig = next(p for p in data["platforms"] if p["platform"] == "instagram")
        assert ig["enabled"] is True
        assert ig["delay_hours"] == 2

    def test_update_existing_config(self, client):
        # Create first
        client.put(
            "/api/settings/publish",
            json={"platforms": [{"platform": "instagram", "enabled": True, "delay_hours": 2}]},
        )
        # Update
        resp = client.put(
            "/api/settings/publish",
            json={"platforms": [{"platform": "instagram", "enabled": False, "delay_hours": 6}]},
        )
        assert resp.status_code == 200
        ig = resp.json()["platforms"][0]
        assert ig["enabled"] is False
        assert ig["delay_hours"] == 6

    def test_config_with_pillar_overrides(self, client):
        resp = client.put(
            "/api/settings/publish",
            json={
                "platforms": [
                    {
                        "platform": "instagram",
                        "enabled": True,
                        "delay_hours": 2,
                        "pillar_overrides": {"spiritual": False, "cow_life": True},
                    }
                ]
            },
        )
        assert resp.status_code == 200
        ig = resp.json()["platforms"][0]
        assert ig["pillar_overrides"]["spiritual"] is False
        assert ig["pillar_overrides"]["cow_life"] is True

    def test_empty_update(self, client):
        resp = client.put("/api/settings/publish", json={"platforms": []})
        assert resp.status_code == 200
        assert resp.json()["platforms"] == []
