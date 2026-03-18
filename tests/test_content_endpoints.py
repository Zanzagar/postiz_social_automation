"""Tests for content endpoints using SQLite backend (Task #4).

Tests verify that content.py endpoints work with ContentRepository
instead of SheetsClient, maintaining backward-compatible response shapes.
"""

import asyncio
import json
from datetime import datetime

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
    """Create an async in-memory SQLite session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def client(_env_vars, db_session):
    """Create test client with SQLite override and auth bypass."""
    from api.dependencies import get_content_repo, get_db
    from api.main import app
    from api.repositories.content import ContentRepository

    repo = ContentRepository(db_session)

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_content_repo] = lambda: repo

    # Bypass auth
    from api.auth import get_current_user

    app.dependency_overrides[get_current_user] = lambda: {"sub": "testuser"}

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture
def seeded_client(client, db_session):
    """Client with pre-seeded content rows."""

    from api.repositories.content import ContentRepository

    repo = ContentRepository(db_session)

    async def seed():
        await repo.create_content_row(
            {
                "raw_text": "Draft content about cows",
                "status": "pending_approval",
                "date": datetime(2026, 3, 20),
                "pillar": "cow_life",
                "platforms": json.dumps({"instagram": True, "facebook": True}),
                "captions": json.dumps(
                    {"instagram": "IG caption about cows", "facebook": "FB caption about cows"}
                ),
                "source": "manual",
            }
        )
        await repo.create_content_row(
            {
                "raw_text": "Approved post about farm",
                "status": "approved",
                "date": datetime(2026, 3, 21),
                "pillar": "farm_ops",
                "platforms": json.dumps({"instagram": True}),
                "captions": json.dumps({"instagram": "Farm update caption"}),
                "source": "manual",
            }
        )
        await repo.create_content_row(
            {
                "raw_text": "Posted spiritual content",
                "status": "posted",
                "date": datetime(2026, 3, 18),
                "pillar": "spiritual",
                "platforms": json.dumps({"instagram": True}),
                "captions": json.dumps({"instagram": "Spiritual post"}),
                "source": "sheet",
                "sheet_row_number": 5,
            }
        )

    asyncio.get_event_loop().run_until_complete(seed())
    return client


# --- GET /api/drafts ---


class TestGetDrafts:
    def test_returns_pending_approval_rows(self, seeded_client):
        resp = seeded_client.get("/api/drafts")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["raw_text"] == "Draft content about cows"
        assert data[0]["status"] == "pending_approval"

    def test_response_shape_matches_schema(self, seeded_client):
        resp = seeded_client.get("/api/drafts")
        row = resp.json()[0]
        assert "row_number" in row
        assert "date" in row
        assert "content_pillar" in row
        assert "raw_text" in row
        assert "platforms" in row
        assert "status" in row
        assert "captions" in row
        assert isinstance(row["platforms"], dict)
        assert isinstance(row["captions"], dict)

    def test_empty_drafts(self, client):
        resp = client.get("/api/drafts")
        assert resp.status_code == 200
        assert resp.json() == []


# --- GET /api/calendar ---


class TestGetCalendar:
    def test_returns_approved_scheduled_posted(self, seeded_client):
        resp = seeded_client.get("/api/calendar")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2  # approved + posted (no scheduled in seed)
        assert len(data["entries"]) == 2

    def test_calendar_entries_sorted_by_date(self, seeded_client):
        resp = seeded_client.get("/api/calendar")
        entries = resp.json()["entries"]
        dates = [e["date"] for e in entries]
        assert dates == sorted(dates)

    def test_calendar_entry_shape(self, seeded_client):
        resp = seeded_client.get("/api/calendar")
        entry = resp.json()["entries"][0]
        assert "row_number" in entry
        assert "date" in entry
        assert "content_pillar" in entry
        assert "raw_text" in entry
        assert "status" in entry
        assert "platforms" in entry
        assert "captions" in entry


# --- GET /api/content/{row_number} ---


class TestGetContentRow:
    def test_returns_row_by_id(self, seeded_client):
        resp = seeded_client.get("/api/content/1")
        assert resp.status_code == 200
        assert resp.json()["raw_text"] == "Draft content about cows"

    def test_404_for_missing_row(self, seeded_client):
        resp = seeded_client.get("/api/content/999")
        assert resp.status_code == 404


# --- POST /api/drafts/{row_number}/edit ---


class TestEditDraft:
    def test_updates_captions(self, seeded_client):
        resp = seeded_client.post(
            "/api/drafts/1/edit",
            json={"captions": {"instagram": "Updated IG", "facebook": "Updated FB"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["captions"]["instagram"] == "Updated IG"
        assert data["captions"]["facebook"] == "Updated FB"

    def test_404_for_missing_row(self, seeded_client):
        resp = seeded_client.post(
            "/api/drafts/999/edit",
            json={"captions": {"instagram": "test"}},
        )
        assert resp.status_code == 404


# --- POST /api/drafts/{row_number}/approve ---


class TestApproveDraft:
    def test_approves_and_creates_postiz_drafts(self, seeded_client):
        # Mock Postiz client
        from unittest.mock import MagicMock

        from api.dependencies import get_postiz_client
        from api.main import app

        mock_postiz = MagicMock()
        mock_postiz.list_integrations.return_value = [
            {"id": "ig-1", "identifier": "instagram", "name": "IG"},
            {"id": "fb-1", "identifier": "facebook", "name": "FB"},
        ]
        mock_postiz.create_draft_post.return_value = {"id": "draft-123"}
        app.dependency_overrides[get_postiz_client] = lambda: mock_postiz

        resp = seeded_client.post("/api/drafts/1/approve")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["postiz_ids"]) > 0

    def test_404_for_missing_row(self, seeded_client):
        resp = seeded_client.post("/api/drafts/999/approve")
        assert resp.status_code == 404
