"""Tests for content templates CRUD API (Task #6).

Tests cover:
- GET /api/templates — list all templates
- POST /api/templates — create a new template
- GET /api/templates/{id} — get single template
- PUT /api/templates/{id} — update template
- DELETE /api/templates/{id} — delete template
- POST /api/templates/{id}/generate — variable substitution + caption generation
"""

import asyncio
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
        Platform.INSTAGRAM: "Generated IG caption from template",
        Platform.FACEBOOK: "Generated FB caption from template",
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


@pytest.fixture
def seeded_client(client, repo):
    """Client with a pre-seeded template."""
    asyncio.get_event_loop().run_until_complete(
        repo.create_template(
            {
                "name": "Sunday Feast",
                "pillar": "community",
                "raw_text_template": "Join us this {{day}} for our weekly Love Feast at {{time}}!",
                "variables": json.dumps(
                    [
                        {"name": "day", "type": "text"},
                        {"name": "time", "type": "text"},
                    ]
                ),
                "platform_instructions": json.dumps({"instagram": "Add 5 hashtags"}),
                "schedule_pattern": "weekly:sunday",
            }
        )
    )
    return client


# --- GET /api/templates ---


class TestListTemplates:
    def test_empty_list(self, client):
        resp = client.get("/api/templates")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_templates(self, seeded_client):
        resp = seeded_client.get("/api/templates")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "Sunday Feast"


# --- POST /api/templates ---


class TestCreateTemplate:
    def test_create_template(self, client):
        resp = client.post(
            "/api/templates",
            json={
                "name": "Weekly Verse",
                "pillar": "spiritual",
                "raw_text_template": "Verse of the week: {{verse}} — {{reference}}",
                "variables": [
                    {"name": "verse", "type": "text"},
                    {"name": "reference", "type": "text"},
                ],
                "schedule_pattern": "weekly:monday",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Weekly Verse"
        assert data["id"] is not None
        assert len(data["variables"]) == 2

    def test_create_template_minimal(self, client):
        resp = client.post(
            "/api/templates",
            json={
                "name": "Quick Post",
                "raw_text_template": "{{content}}",
                "variables": [{"name": "content", "type": "text"}],
            },
        )
        assert resp.status_code == 200
        assert resp.json()["pillar"] is None


# --- GET /api/templates/{id} ---


class TestGetTemplate:
    def test_get_template(self, seeded_client):
        resp = seeded_client.get("/api/templates/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Sunday Feast"
        assert "variables" in data
        assert "platform_instructions" in data

    def test_get_template_404(self, client):
        resp = client.get("/api/templates/999")
        assert resp.status_code == 404


# --- PUT /api/templates/{id} ---


class TestUpdateTemplate:
    def test_update_template(self, seeded_client):
        resp = seeded_client.put(
            "/api/templates/1",
            json={
                "name": "Sunday Love Feast",
                "raw_text_template": "Join us {{day}} at {{time}} for kirtan and prasadam!",
                "variables": [
                    {"name": "day", "type": "text"},
                    {"name": "time", "type": "text"},
                ],
            },
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Sunday Love Feast"

    def test_update_template_404(self, client):
        resp = client.put(
            "/api/templates/999",
            json={
                "name": "Nonexistent",
                "raw_text_template": "test",
                "variables": [],
            },
        )
        assert resp.status_code == 404


# --- DELETE /api/templates/{id} ---


class TestDeleteTemplate:
    def test_delete_template(self, seeded_client):
        resp = seeded_client.delete("/api/templates/1")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

        # Verify it's gone
        resp = seeded_client.get("/api/templates/1")
        assert resp.status_code == 404


# --- POST /api/templates/{id}/generate ---


class TestGenerateFromTemplate:
    def test_generate_substitutes_variables(self, seeded_client):
        resp = seeded_client.post(
            "/api/templates/1/generate",
            json={
                "variable_values": {"day": "Sunday", "time": "5pm"},
                "platforms": ["instagram", "facebook"],
                "scheduled_date": "2026-03-22",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["source"] == "template"
        assert "row_number" in data

    def test_generate_missing_variables_returns_400(self, seeded_client):
        resp = seeded_client.post(
            "/api/templates/1/generate",
            json={
                "variable_values": {"day": "Sunday"},  # missing "time"
                "platforms": ["instagram"],
                "scheduled_date": "2026-03-22",
            },
        )
        assert resp.status_code == 400
        assert "time" in resp.json()["detail"]

    def test_generate_template_404(self, client):
        resp = client.post(
            "/api/templates/999/generate",
            json={
                "variable_values": {},
                "platforms": ["instagram"],
                "scheduled_date": "2026-03-22",
            },
        )
        assert resp.status_code == 404

    def test_generate_creates_content_row(self, seeded_client, repo):
        seeded_client.post(
            "/api/templates/1/generate",
            json={
                "variable_values": {"day": "Sunday", "time": "5pm"},
                "platforms": ["instagram"],
                "scheduled_date": "2026-03-22",
            },
        )

        rows = asyncio.get_event_loop().run_until_complete(repo.get_all_content_rows())
        assert len(rows) == 1
        assert rows[0].template_id == 1
        assert rows[0].source == "template"
        assert "5pm" in rows[0].raw_text
