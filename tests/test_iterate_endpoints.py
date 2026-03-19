"""Tests for AI content iteration endpoints (Task #5).

Tests cover:
- POST /api/iterate — regenerate a single platform caption
- GET /api/iterations/{content_id} — iteration history
- Iteration saved to database
- Content row captions updated after iteration
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import MagicMock

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
def mock_generator():
    gen = MagicMock()
    gen.iterate_single_caption.return_value = "Improved caption with more warmth and detail"
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

    # Seed a content row
    asyncio.get_event_loop().run_until_complete(
        repo.create_content_row(
            {
                "raw_text": "Morning at the barn with Lakshmi",
                "status": "draft",
                "date": datetime(2026, 3, 20),
                "pillar": "cow_life",
                "platforms": json.dumps({"instagram": True, "facebook": True}),
                "captions": json.dumps(
                    {"instagram": "Original IG caption", "facebook": "Original FB caption"}
                ),
                "source": "generated",
            }
        )
    )

    yield TestClient(app)
    app.dependency_overrides.clear()


class TestIterateCaption:
    def test_iterate_returns_new_caption(self, client):
        resp = client.post(
            "/api/iterate",
            json={
                "content_row_id": 1,
                "platform": "instagram",
                "instruction": "Make it more casual",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "caption" in data
        assert "iteration_id" in data
        assert data["caption"] == "Improved caption with more warmth and detail"

    def test_iterate_404_for_missing_row(self, client):
        resp = client.post(
            "/api/iterate",
            json={
                "content_row_id": 999,
                "platform": "instagram",
                "instruction": "Make it shorter",
            },
        )
        assert resp.status_code == 404

    def test_iterate_saves_iteration(self, client, repo):
        client.post(
            "/api/iterate",
            json={
                "content_row_id": 1,
                "platform": "instagram",
                "instruction": "Add a call to action",
                "mode": "refine",
            },
        )

        iterations = asyncio.get_event_loop().run_until_complete(repo.get_iterations(1))
        assert len(iterations) == 1
        assert iterations[0].platform == "instagram"
        assert iterations[0].old_caption == "Original IG caption"
        assert iterations[0].refinement_instruction == "Add a call to action"
        assert iterations[0].mode == "refine"

    def test_iterate_updates_content_row_captions(self, client, repo):
        client.post(
            "/api/iterate",
            json={
                "content_row_id": 1,
                "platform": "instagram",
                "instruction": "Make it warmer",
            },
        )

        row = asyncio.get_event_loop().run_until_complete(repo.get_content_row(1))
        captions = json.loads(row.captions)
        assert captions["instagram"] == "Improved caption with more warmth and detail"
        # Facebook caption should be unchanged
        assert captions["facebook"] == "Original FB caption"

    def test_iterate_with_repurpose_mode(self, client):
        resp = client.post(
            "/api/iterate",
            json={
                "content_row_id": 1,
                "platform": "facebook",
                "instruction": "Repurpose for Facebook audience",
                "mode": "repurpose",
            },
        )
        assert resp.status_code == 200

    def test_iterate_calls_generator_with_correct_args(self, client, mock_generator):
        client.post(
            "/api/iterate",
            json={
                "content_row_id": 1,
                "platform": "instagram",
                "instruction": "Shorten it",
            },
        )
        mock_generator.iterate_single_caption.assert_called_once_with(
            original_caption="Original IG caption",
            platform="instagram",
            instruction="Shorten it",
            raw_text="Morning at the barn with Lakshmi",
            pillar="cow_life",
        )


class TestGetIterations:
    def test_get_iterations_empty(self, client):
        resp = client.get("/api/iterations/1")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_iterations_after_iterate(self, client):
        # Create an iteration first
        client.post(
            "/api/iterate",
            json={
                "content_row_id": 1,
                "platform": "instagram",
                "instruction": "Add emojis",
            },
        )

        resp = client.get("/api/iterations/1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["platform"] == "instagram"
        assert data[0]["refinement_instruction"] == "Add emojis"
        assert "created_at" in data[0]

    def test_get_iterations_multiple(self, client):
        # Two iterations
        client.post(
            "/api/iterate",
            json={"content_row_id": 1, "platform": "instagram", "instruction": "First revision"},
        )
        client.post(
            "/api/iterate",
            json={"content_row_id": 1, "platform": "facebook", "instruction": "Second revision"},
        )

        resp = client.get("/api/iterations/1")
        assert resp.status_code == 200
        assert len(resp.json()) == 2
