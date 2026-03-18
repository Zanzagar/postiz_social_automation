"""Tests for API route endpoints (content, generate, postiz, health, upload)."""

import asyncio
import io
import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.models import Base
from content_engine.models import ContentPillar, Platform, Suggestion


@pytest.fixture(autouse=True)
def _clear_caches():
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


def _make_suggestion() -> Suggestion:
    return Suggestion(
        suggested_date=datetime(2026, 3, 20),
        content_idea="Post about spring calves",
        suggested_pillar=ContentPillar.COW_LIFE,
        rationale="No cow content in 5 days",
        media_suggestion="Photo of new calves in pasture",
        status="suggested",
    )


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
def mock_sheets():
    mock = MagicMock()
    mock.get_suggestions.return_value = [_make_suggestion()]
    mock.get_recent_errors.return_value = []
    return mock


@pytest.fixture
def mock_postiz():
    mock = MagicMock()
    mock.list_integrations.return_value = [
        {"id": "int-1", "identifier": "instagram", "name": "Gita Valley IG"},
        {"id": "int-2", "identifier": "facebook", "name": "Gita Valley FB"},
    ]
    mock.create_draft_post.return_value = {"id": "draft-123"}
    return mock


@pytest.fixture
def mock_generator():
    mock = MagicMock()
    mock.generate_captions.return_value = {
        Platform.INSTAGRAM: "Generated IG caption",
        Platform.FACEBOOK: "Generated FB caption",
    }
    return mock


@pytest.fixture
def client(_env_vars, db_session, repo, mock_sheets, mock_postiz, mock_generator):
    from api.auth import _failed_attempts
    from api.routes.health import _health_cache

    _failed_attempts.clear()
    _health_cache["data"] = None
    _health_cache["expires"] = 0

    from api.main import app

    app.dependency_overrides = {}

    from api.dependencies import (
        get_caption_generator,
        get_content_repo,
        get_db,
        get_postiz_client,
        get_sheets_client,
    )

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_content_repo] = lambda: repo
    app.dependency_overrides[get_sheets_client] = lambda: mock_sheets
    app.dependency_overrides[get_postiz_client] = lambda: mock_postiz
    app.dependency_overrides[get_caption_generator] = lambda: mock_generator

    # Seed test data
    asyncio.get_event_loop().run_until_complete(
        repo.create_content_row(
            {
                "raw_text": "Beautiful morning with the cows",
                "status": "pending_approval",
                "date": datetime(2026, 3, 15),
                "pillar": "cow_life",
                "platforms": json.dumps({"instagram": True, "facebook": True}),
                "captions": json.dumps({"instagram": "test caption", "facebook": "fb caption"}),
                "source": "manual",
            }
        )
    )
    asyncio.get_event_loop().run_until_complete(
        repo.create_content_row(
            {
                "raw_text": "Approved farm content",
                "status": "approved",
                "date": datetime(2026, 3, 16),
                "pillar": "farm_ops",
                "platforms": json.dumps({"instagram": True}),
                "captions": json.dumps({"instagram": "approved caption"}),
                "source": "manual",
            }
        )
    )

    c = TestClient(app)
    yield c
    app.dependency_overrides = {}


def _auth_header(client) -> dict:
    resp = client.post("/api/auth/login", json={"password": "testpass"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# --- Content endpoints ---


class TestDraftsEndpoint:
    def test_get_drafts_requires_auth(self, client):
        assert client.get("/api/drafts").status_code == 401

    def test_get_drafts_returns_rows(self, client):
        headers = _auth_header(client)
        response = client.get("/api/drafts", headers=headers)
        assert response.status_code == 200
        data = response.json()
        # Returns all pre-published rows (pending_approval + approved)
        assert len(data) == 2
        statuses = {d["status"] for d in data}
        assert "pending_approval" in statuses
        assert "approved" in statuses


class TestCalendarEndpoint:
    def test_get_calendar(self, client):
        headers = _auth_header(client)
        response = client.get("/api/calendar", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert "total" in data
        assert data["total"] == 2  # pending_approval + approved


class TestSuggestionsEndpoint:
    def test_get_suggestions(self, client, mock_sheets):
        headers = _auth_header(client)
        response = client.get("/api/suggestions", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["content_idea"] == "Post about spring calves"

    def test_get_suggestions_with_filter(self, client, mock_sheets):
        headers = _auth_header(client)
        client.get("/api/suggestions?status=suggested", headers=headers)
        mock_sheets.get_suggestions.assert_called_with(status="suggested")


class TestContentRowEndpoint:
    def test_get_content_row(self, client):
        headers = _auth_header(client)
        response = client.get("/api/content/1", headers=headers)
        assert response.status_code == 200
        assert response.json()["row_number"] == 1

    def test_get_content_row_not_found(self, client):
        headers = _auth_header(client)
        response = client.get("/api/content/999", headers=headers)
        assert response.status_code == 404


class TestEditDraftEndpoint:
    def test_edit_draft(self, client):
        headers = _auth_header(client)
        response = client.post(
            "/api/drafts/1/edit",
            json={"captions": {"instagram": "new caption"}},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["captions"]["instagram"] == "new caption"


class TestApproveDraft:
    def test_approve_draft(self, client, mock_postiz):
        headers = _auth_header(client)
        response = client.post("/api/drafts/1/approve", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "postiz_ids" in data

    def test_approve_nonexistent_row(self, client):
        headers = _auth_header(client)
        response = client.post("/api/drafts/999/approve", headers=headers)
        assert response.status_code == 404


# --- Generate endpoints ---


class TestGenerateEndpoint:
    def test_generate_requires_auth(self, client):
        assert client.post("/api/generate", json={}).status_code == 401

    def test_generate_streams_sse(self, client, mock_generator):
        headers = _auth_header(client)
        response = client.post(
            "/api/generate",
            json={
                "raw_text": "Cows in the field",
                "platforms": ["instagram"],
                "scheduled_date": "2026-03-20",
            },
            headers=headers,
        )
        assert response.status_code == 200
        assert "done" in response.text


class TestRepromptEndpoint:
    def test_reprompt(self, client, mock_generator):
        headers = _auth_header(client)
        response = client.post(
            "/api/reprompt",
            json={
                "raw_text": "Cows in the field",
                "platforms": ["instagram"],
                "scheduled_date": "2026-03-20",
                "feedback": "Make it funnier",
            },
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "captions" in data


# --- Postiz endpoints ---


class TestSendToPostiz:
    def test_send_to_postiz(self, client, mock_postiz):
        headers = _auth_header(client)
        response = client.post(
            "/api/send-to-postiz",
            json={"captions": {"instagram": "My post"}},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "draft_ids" in data

    def test_list_integrations(self, client, mock_postiz):
        headers = _auth_header(client)
        response = client.get("/api/integrations", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["platform"] == "instagram"


# --- Health endpoint ---


class TestSystemHealth:
    @patch("api.routes.health.check_sheets_health", return_value=(True, "Connected"))
    @patch("api.routes.health.check_postiz_health", return_value=(True, "Connected"))
    @patch("api.routes.health.check_claude_health", return_value=(True, "Available"))
    @patch("api.routes.health.check_oauth_health", return_value=(True, "Valid"))
    def test_health_check(self, _m1, _m2, _m3, _m4, client, mock_sheets):
        headers = _auth_header(client)
        response = client.get("/api/health", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["services"]) == 4
        assert all(s["status"] == "ok" for s in data["services"])


# --- Upload endpoint ---


class TestUpload:
    def test_upload_requires_auth(self, client):
        assert client.post("/api/upload").status_code == 401

    def test_upload_valid_image(self, client):
        headers = _auth_header(client)
        file_content = b"\xff\xd8\xff\xe0" + b"\x00" * 100  # Fake JPEG
        response = client.post(
            "/api/upload",
            files={"file": ("test.jpg", io.BytesIO(file_content), "image/jpeg")},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content_type"] == "image/jpeg"
        assert data["size"] == 104

    def test_upload_rejects_unsupported_type(self, client):
        headers = _auth_header(client)
        response = client.post(
            "/api/upload",
            files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
            headers=headers,
        )
        assert response.status_code == 400
        assert "Unsupported" in response.json()["detail"]
