"""Tests for generate endpoints with SQLite persistence (Task #4.3).

Tests verify that generated content is persisted to SQLite.
"""

import json
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.models import Base
from content_engine.models import Platform


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
def mock_generator():
    gen = MagicMock()
    gen.generate_captions.return_value = {
        Platform.INSTAGRAM: "Generated IG caption #GitaValley",
        Platform.FACEBOOK: "Generated FB caption for Gita Valley",
    }
    return gen


@pytest.fixture
def client(_env_vars, db_session, repo, mock_generator):
    from api.auth import get_current_user
    from api.dependencies import get_caption_generator, get_content_repo, get_db
    from api.main import app

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_content_repo] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: {"sub": "testuser"}
    app.dependency_overrides[get_caption_generator] = lambda: mock_generator

    yield TestClient(app)

    app.dependency_overrides.clear()


class TestGenerateSync:
    def test_returns_captions(self, client):
        resp = client.post(
            "/api/generate-sync",
            json={
                "raw_text": "Morning at the barn with cows",
                "platforms": ["instagram", "facebook"],
                "scheduled_date": "2026-03-20",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "captions" in data
        assert "instagram" in data["captions"]
        assert "facebook" in data["captions"]

    def test_returns_row_id(self, client):
        resp = client.post(
            "/api/generate-sync",
            json={
                "raw_text": "Farm update content",
                "platforms": ["instagram"],
                "scheduled_date": "2026-03-21",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "row_id" in data
        assert isinstance(data["row_id"], int)

    def test_persists_to_sqlite(self, client, repo):
        import asyncio

        resp = client.post(
            "/api/generate-sync",
            json={
                "raw_text": "Content to persist",
                "platforms": ["instagram", "facebook"],
                "scheduled_date": "2026-03-22",
            },
        )
        row_id = resp.json()["row_id"]

        row = asyncio.get_event_loop().run_until_complete(repo.get_content_row(row_id))
        assert row is not None
        assert row.raw_text == "Content to persist"
        assert row.status == "draft"
        assert row.source == "generated"

        captions = json.loads(row.captions)
        assert "instagram" in captions


class TestReprompt:
    def test_returns_captions_with_feedback(self, client, mock_generator):
        mock_generator.generate_captions.return_value = {
            Platform.INSTAGRAM: "Revised IG caption",
        }
        resp = client.post(
            "/api/reprompt",
            json={
                "raw_text": "Farm update",
                "platforms": ["instagram"],
                "scheduled_date": "2026-03-20",
                "feedback": "Make it more casual",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "captions" in data
        assert "row_id" in data

    def test_persists_reprompted_content(self, client, repo):
        import asyncio

        resp = client.post(
            "/api/reprompt",
            json={
                "raw_text": "Reprompted content",
                "platforms": ["instagram"],
                "scheduled_date": "2026-03-20",
                "feedback": "Shorten it",
            },
        )
        row_id = resp.json()["row_id"]

        row = asyncio.get_event_loop().run_until_complete(repo.get_content_row(row_id))
        assert row is not None
        assert row.source == "generated"
