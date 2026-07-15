"""Tests for the SQLite-backed /api/suggestions endpoints.

The clock is frozen by monkeypatching api.routes.suggestions._today —
never asserted against wall-clock now.
"""

import asyncio
import json
from datetime import date, datetime, time, timedelta

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.models import Base, ContentRow, Suggestion

TODAY = date(2026, 8, 1)

_key_counter = 0


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


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
def client(_env_vars, db_session, monkeypatch):
    import api.routes.suggestions as suggestions_route
    from api.auth import _failed_attempts
    from api.dependencies import get_content_repo, get_db
    from api.main import app
    from api.repositories.content import ContentRepository

    _failed_attempts.clear()
    monkeypatch.setattr(suggestions_route, "_today", lambda: TODAY)

    app.dependency_overrides = {}

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_content_repo] = lambda: ContentRepository(db_session)

    c = TestClient(app)
    yield c
    app.dependency_overrides = {}


@pytest.fixture
def auth_headers(client):
    resp = client.post("/api/auth/login", json={"password": "testpass"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed(db_session, **overrides) -> Suggestion:
    """Insert a Suggestion row with sensible defaults."""
    global _key_counter
    _key_counter += 1
    data = {
        "type": "festival",
        "title": f"Suggestion {_key_counter}",
        "note": "A note.",
        "pillar": None,
        "suggested_date": None,
        "status": "suggested",
        "source_key": f"test:key:{_key_counter}",
    }
    data.update(overrides)

    async def _add():
        suggestion = Suggestion(**data)
        db_session.add(suggestion)
        await db_session.commit()
        await db_session.refresh(suggestion)
        return suggestion

    return _run(_add())


def _write_calendar(tmp_path, festivals):
    path = tmp_path / "calendar.json"
    path.write_text(json.dumps(festivals))
    return path


# --- GET /api/suggestions ---


class TestGetSuggestions:
    def test_requires_auth(self, client):
        assert client.get("/api/suggestions").status_code == 401

    def test_empty_table_returns_wellformed(self, client, auth_headers):
        resp = client.get("/api/suggestions", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == {"suggestions": []}

    def test_default_filter_returns_only_suggested(self, client, auth_headers, db_session):
        _seed(db_session, title="Keep me")
        _seed(db_session, title="Dismissed", status="dismissed")
        _seed(db_session, title="Drafted", status="drafted")

        resp = client.get("/api/suggestions", headers=auth_headers)
        data = resp.json()["suggestions"]
        assert [s["title"] for s in data] == ["Keep me"]
        assert data[0]["status"] == "suggested"

    def test_status_all_returns_everything(self, client, auth_headers, db_session):
        _seed(db_session)
        _seed(db_session, status="dismissed")
        _seed(db_session, status="drafted")

        resp = client.get("/api/suggestions?status=all", headers=auth_headers)
        assert len(resp.json()["suggestions"]) == 3

    def test_status_dismissed_filter(self, client, auth_headers, db_session):
        _seed(db_session)
        _seed(db_session, title="Gone", status="dismissed")

        resp = client.get("/api/suggestions?status=dismissed", headers=auth_headers)
        data = resp.json()["suggestions"]
        assert [s["title"] for s in data] == ["Gone"]

    def test_ordering_dated_asc_then_undated_created_desc(self, client, auth_headers, db_session):
        _seed(
            db_session,
            title="Later fest",
            suggested_date=TODAY + timedelta(days=20),
        )
        _seed(
            db_session,
            title="Sooner fest",
            suggested_date=TODAY + timedelta(days=5),
        )
        _seed(
            db_session,
            title="Old undated",
            created_at=datetime.combine(TODAY - timedelta(days=3), time.min),
        )
        _seed(
            db_session,
            title="New undated",
            created_at=datetime.combine(TODAY - timedelta(days=1), time.min),
        )

        resp = client.get("/api/suggestions", headers=auth_headers)
        titles = [s["title"] for s in resp.json()["suggestions"]]
        assert titles == ["Sooner fest", "Later fest", "New undated", "Old undated"]

    def test_days_until_and_date_serialization(self, client, auth_headers, db_session):
        _seed(db_session, title="Future", suggested_date=TODAY + timedelta(days=10))
        _seed(db_session, title="Past", suggested_date=TODAY - timedelta(days=3))
        _seed(db_session, title="Undated")

        resp = client.get("/api/suggestions", headers=auth_headers)
        by_title = {s["title"]: s for s in resp.json()["suggestions"]}
        assert by_title["Future"]["days_until"] == 10
        assert by_title["Future"]["date"] == (TODAY + timedelta(days=10)).isoformat()
        assert by_title["Past"]["days_until"] == -3
        assert by_title["Undated"]["days_until"] is None
        assert by_title["Undated"]["date"] is None

    def test_item_shape(self, client, auth_headers, db_session):
        _seed(
            db_session,
            title="Janmashtami",
            note="Krishna's appearance day.",
            pillar="spiritual_education",
            suggested_date=TODAY + timedelta(days=7),
        )
        resp = client.get("/api/suggestions", headers=auth_headers)
        [item] = resp.json()["suggestions"]
        assert set(item.keys()) == {
            "id",
            "type",
            "title",
            "note",
            "pillar",
            "date",
            "days_until",
            "status",
        }
        assert item["pillar"] == "spiritual_education"


# --- POST /api/suggestions/refresh ---


class TestRefreshEndpoint:
    def test_requires_auth(self, client):
        assert client.post("/api/suggestions/refresh").status_code == 401

    def test_refresh_creates_festival_suggestions(
        self, client, auth_headers, monkeypatch, tmp_path
    ):
        fest_date = TODAY + timedelta(days=10)
        path = _write_calendar(
            tmp_path,
            [
                {
                    "name": "Janmashtami",
                    "date": fest_date.isoformat(),
                    "significance": "Appearance day of Lord Krishna.",
                    "suggested_content_angles": ["Share midnight kirtan plans"],
                    "topic": "Spiritual Life",
                    "content_pillar": "spiritual_education",
                }
            ],
        )
        monkeypatch.setattr("api.services.suggestion_generator.CALENDAR_PATH", path)

        resp = client.post("/api/suggestions/refresh", headers=auth_headers)
        assert resp.status_code == 200
        [item] = resp.json()["suggestions"]
        assert item["type"] == "festival"
        assert item["title"] == "Janmashtami"
        assert item["date"] == fest_date.isoformat()
        assert item["days_until"] == 10
        assert item["status"] == "suggested"

    def test_refresh_does_not_resurrect_dismissed(
        self, client, auth_headers, monkeypatch, tmp_path
    ):
        path = _write_calendar(
            tmp_path,
            [
                {
                    "name": "Fest",
                    "date": (TODAY + timedelta(days=5)).isoformat(),
                    "significance": "Sig.",
                    "suggested_content_angles": ["Angle"],
                    "topic": "Spiritual Life",
                    "content_pillar": "events",
                }
            ],
        )
        monkeypatch.setattr("api.services.suggestion_generator.CALENDAR_PATH", path)

        resp = client.post("/api/suggestions/refresh", headers=auth_headers)
        [item] = resp.json()["suggestions"]

        dismiss = client.post(f"/api/suggestions/{item['id']}/dismiss", headers=auth_headers)
        assert dismiss.status_code == 200

        resp = client.post("/api/suggestions/refresh", headers=auth_headers)
        assert resp.json()["suggestions"] == []

        all_resp = client.get("/api/suggestions?status=all", headers=auth_headers)
        [row] = all_resp.json()["suggestions"]
        assert row["status"] == "dismissed"


# --- POST /api/suggestions/{id}/dismiss ---


class TestDismissEndpoint:
    def test_dismiss(self, client, auth_headers, db_session):
        suggestion = _seed(db_session)
        resp = client.post(f"/api/suggestions/{suggestion.id}/dismiss", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == {"id": suggestion.id, "status": "dismissed"}

    def test_dismiss_is_idempotent(self, client, auth_headers, db_session):
        """Repeating a dismiss returns 200 with the same body."""
        suggestion = _seed(db_session)
        first = client.post(f"/api/suggestions/{suggestion.id}/dismiss", headers=auth_headers)
        second = client.post(f"/api/suggestions/{suggestion.id}/dismiss", headers=auth_headers)
        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json() == {"id": suggestion.id, "status": "dismissed"}

    def test_dismiss_missing_returns_404(self, client, auth_headers):
        resp = client.post("/api/suggestions/9999/dismiss", headers=auth_headers)
        assert resp.status_code == 404

    def test_requires_auth(self, client, db_session):
        suggestion = _seed(db_session)
        assert client.post(f"/api/suggestions/{suggestion.id}/dismiss").status_code == 401


# --- POST /api/suggestions/{id}/draft ---


class TestDraftEndpoint:
    def test_draft_creates_content_row(self, client, auth_headers, db_session):
        fest_date = TODAY + timedelta(days=7)
        suggestion = _seed(
            db_session,
            title="Janmashtami",
            note="Krishna's appearance day.",
            pillar="spiritual_education",
            suggested_date=fest_date,
        )

        resp = client.post(f"/api/suggestions/{suggestion.id}/draft", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == suggestion.id
        assert body["status"] == "drafted"
        assert isinstance(body["content_row_id"], int)

        row = _run(db_session.get(ContentRow, body["content_row_id"]))
        assert row.status == "draft"
        assert row.pillar == "spiritual_education"
        assert row.raw_text == "Janmashtami — Krishna's appearance day."
        assert row.date == datetime.combine(fest_date, time.min)

        updated = _run(db_session.get(Suggestion, suggestion.id))
        assert updated.status == "drafted"
        assert updated.content_row_id == body["content_row_id"]

    def test_draft_without_date_leaves_row_date_unset(self, client, auth_headers, db_session):
        suggestion = _seed(db_session, title="Idea", note="N.", pillar="events")
        resp = client.post(f"/api/suggestions/{suggestion.id}/draft", headers=auth_headers)
        assert resp.status_code == 200
        row = _run(db_session.get(ContentRow, resp.json()["content_row_id"]))
        assert row.date is None

    def test_redraft_is_idempotent(self, client, auth_headers, db_session):
        """Re-drafting returns the existing content_row_id without a new row."""
        suggestion = _seed(db_session, title="Idea", note="N.")
        first = client.post(f"/api/suggestions/{suggestion.id}/draft", headers=auth_headers)
        second = client.post(f"/api/suggestions/{suggestion.id}/draft", headers=auth_headers)

        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json() == first.json()

        result = _run(db_session.execute(select(func.count()).select_from(ContentRow)))
        assert result.scalar_one() == 1

    def test_draft_dismissed_returns_409(self, client, auth_headers, db_session):
        """A dismissed suggestion must not be resurrected by drafting."""
        suggestion = _seed(db_session, status="dismissed")
        resp = client.post(f"/api/suggestions/{suggestion.id}/draft", headers=auth_headers)
        assert resp.status_code == 409
        assert resp.json() == {"detail": "Suggestion was dismissed"}

        result = _run(db_session.execute(select(func.count()).select_from(ContentRow)))
        assert result.scalar_one() == 0
        updated = _run(db_session.get(Suggestion, suggestion.id))
        assert updated.status == "dismissed"

    def test_draft_missing_returns_404(self, client, auth_headers):
        resp = client.post("/api/suggestions/9999/draft", headers=auth_headers)
        assert resp.status_code == 404

    def test_requires_auth(self, client, db_session):
        suggestion = _seed(db_session)
        assert client.post(f"/api/suggestions/{suggestion.id}/draft").status_code == 401
