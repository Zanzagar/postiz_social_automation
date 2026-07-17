"""Tests for POST /api/content/{row_id}/publish-now and error_msg exposure.

Manual publish semantics (contract W1 item 3): an explicit human click
overrides the auto-release-only gates (require_review, pillar exceptions,
held_at — the hold is cleared first), but NO-ALT is a hard block and the
shared hourly Postiz request budget still applies. Platforms already in
postiz_ids are skipped (idempotent). Row status/postiz_ids updates are
identical to the release loop.
"""

import asyncio
import json
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.models import Base
from api.services.auto_publish import parse_last_publish_failure
from content_engine.postiz import PostizAPIError

# --- Fixtures (pattern from test_auto_publish.py) ---


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    from api.dependencies import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _reset_request_budget():
    """The rolling request window is module-level state; isolate tests."""
    from api.services import auto_publish

    auto_publish._request_times.clear()
    yield
    auto_publish._request_times.clear()


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


class FakePostiz:
    """Fake Postiz client with optional per-integration failures and releaseURL."""

    INTEGRATIONS = [
        {"id": "ig-1", "identifier": "instagram", "name": "IG"},
        {"id": "fb-1", "identifier": "facebook", "name": "FB"},
    ]

    def __init__(self):
        self.fail_integrations = set()
        self.release_url = None  # e.g. "https://postiz.example/p" -> link per post
        self.publish_calls = []
        self.list_calls = 0
        self._counter = 0

    def list_integrations(self):
        self.list_calls += 1
        return self.INTEGRATIONS

    def publish_post(self, content, platform_ids, media_url=None, scheduled_at=None):
        self.publish_calls.append(
            {
                "content": content,
                "platform_ids": platform_ids,
                "media_url": media_url,
                "scheduled_at": scheduled_at,
            }
        )
        if platform_ids[0] in self.fail_integrations:
            raise PostizAPIError("simulated failure")
        self._counter += 1
        result = {"id": f"pub-{self._counter}"}
        if self.release_url:
            result["releaseURL"] = f"{self.release_url}/{self._counter}"
        return result


@pytest.fixture
def fake_postiz():
    return FakePostiz()


@pytest.fixture
def client(_env_vars, db_session, repo, fake_postiz):
    from api.auth import get_current_user
    from api.dependencies import get_content_repo, get_db, get_postiz_client
    from api.main import app

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_content_repo] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: {"sub": "testuser"}
    app.dependency_overrides[get_postiz_client] = lambda: fake_postiz

    yield TestClient(app)

    app.dependency_overrides.clear()


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def seed_row(repo, **overrides):
    data = {
        "raw_text": "Morning milking",
        "status": "approved",
        "date": datetime(2026, 7, 1),
        "pillar": "cow_life",
        "platforms": json.dumps({"instagram": True}),
        "captions": json.dumps({"instagram": "IG caption"}),
        "source": "manual",
    }
    data.update(overrides)

    async def seed():
        row = await repo.create_content_row(data)
        return row.id

    return run(seed())


def get_row(repo, row_id):
    return run(repo.get_content_row(row_id))


def exhaust_budget():
    from api.services import auto_publish

    now = datetime.now(UTC)
    for _ in range(auto_publish.REQUEST_BUDGET_PER_HOUR):
        auto_publish._record_request(now)


# --- Gates ---


class TestPublishNowGates:
    def test_404_unknown_row(self, client):
        assert client.post("/api/content/999/publish-now").status_code == 404

    def test_422_no_alt_when_media_without_alt_text(self, client, repo):
        row_id = seed_row(repo, media_url="https://x.com/a.jpg", alt_text=None)
        resp = client.post(f"/api/content/{row_id}/publish-now")
        assert resp.status_code == 422
        assert resp.json()["detail"] == "alt_text_required"

    def test_429_when_budget_exhausted(self, client, repo, fake_postiz):
        row_id = seed_row(repo)
        exhaust_budget()
        resp = client.post(f"/api/content/{row_id}/publish-now")
        assert resp.status_code == 429
        assert resp.json()["detail"] == (
            "Postiz hourly request budget exhausted — try again in a few minutes"
        )
        assert fake_postiz.publish_calls == []


# --- Success paths ---


class TestPublishNowSuccess:
    def test_publishes_pending_platform_immediately(self, client, repo, fake_postiz):
        row_id = seed_row(repo)
        resp = client.post(f"/api/content/{row_id}/publish-now")
        assert resp.status_code == 200
        body = resp.json()
        assert body["row_id"] == row_id
        assert body["status"] == "posted"
        assert body["posted_at"] is not None
        assert body["results"] == [
            {
                "platform": "instagram",
                "status": "posted",
                "postiz_id": "pub-1",
                "error": None,
                "link": None,
            }
        ]
        row = get_row(repo, row_id)
        assert row.status == "posted"
        assert row.posted_at is not None
        assert json.loads(row.postiz_ids) == {"instagram": "pub-1"}

    def test_link_uses_release_url_when_postiz_returns_it(self, client, repo, fake_postiz):
        fake_postiz.release_url = "https://postiz.example/p"
        row_id = seed_row(repo)
        resp = client.post(f"/api/content/{row_id}/publish-now")
        assert resp.json()["results"][0]["link"] == "https://postiz.example/p/1"

    def test_future_dated_row_is_scheduled(self, client, repo, fake_postiz):
        future = datetime.now(UTC) + timedelta(days=2)
        row_id = seed_row(repo, date=future.replace(tzinfo=None))
        resp = client.post(f"/api/content/{row_id}/publish-now")
        body = resp.json()
        assert body["status"] == "scheduled"
        assert body["posted_at"] is None
        assert body["results"][0]["status"] == "scheduled"
        assert fake_postiz.publish_calls[0]["scheduled_at"] is not None
        row = get_row(repo, row_id)
        assert row.status == "scheduled"
        assert row.posted_at is None

    def test_ignores_require_review_and_missing_publish_config(self, client, repo):
        """Manual publish overrides all auto-release-only gates: a
        require_review row with NO publish config at all still publishes."""
        row_id = seed_row(repo, require_review=True)
        resp = client.post(f"/api/content/{row_id}/publish-now")
        assert resp.status_code == 200
        assert resp.json()["status"] == "posted"

    def test_draft_row_publishes(self, client, repo):
        row_id = seed_row(repo, status="draft")
        resp = client.post(f"/api/content/{row_id}/publish-now")
        assert resp.status_code == 200
        assert resp.json()["status"] == "posted"

    def test_held_row_publishes_and_hold_is_cleared(self, client, repo):
        row_id = seed_row(repo, held_at=datetime(2026, 7, 1, 12, 0, 0))
        resp = client.post(f"/api/content/{row_id}/publish-now")
        assert resp.status_code == 200
        assert resp.json()["status"] == "posted"
        assert get_row(repo, row_id).held_at is None

    def test_http_media_url_passed_through(self, client, repo, fake_postiz):
        row_id = seed_row(repo, media_url="https://example.com/a.jpg", alt_text="A cow")
        client.post(f"/api/content/{row_id}/publish-now")
        assert fake_postiz.publish_calls[0]["media_url"] == "https://example.com/a.jpg"

    def test_drive_proxy_media_is_made_public(self, client, repo, fake_postiz, monkeypatch):
        granted = []
        monkeypatch.setattr(
            "api.services.media_public._ensure_public_drive_permission",
            lambda fid: granted.append(fid),
        )
        row_id = seed_row(repo, media_url="/api/media/drive/file/fid42", alt_text="A cow")
        resp = client.post(f"/api/content/{row_id}/publish-now")
        assert resp.status_code == 200
        assert granted == ["fid42"]
        assert fake_postiz.publish_calls[0]["media_url"] == (
            "https://drive.google.com/uc?export=download&id=fid42"
        )


# --- Idempotency ---


class TestPublishNowIdempotency:
    def test_skips_platforms_already_in_postiz_ids(self, client, repo, fake_postiz):
        row_id = seed_row(
            repo,
            platforms=json.dumps({"instagram": True, "facebook": True}),
            captions=json.dumps({"instagram": "IG cap", "facebook": "FB cap"}),
            postiz_ids=json.dumps({"instagram": "already-1"}),
        )
        resp = client.post(f"/api/content/{row_id}/publish-now")
        body = resp.json()
        assert [r["platform"] for r in body["results"]] == ["facebook"]
        assert [c["platform_ids"] for c in fake_postiz.publish_calls] == [["fb-1"]]
        ids = json.loads(get_row(repo, row_id).postiz_ids)
        assert ids == {"instagram": "already-1", "facebook": "pub-1"}

    def test_fully_published_row_returns_empty_results(self, client, repo, fake_postiz):
        row_id = seed_row(
            repo,
            status="posted",
            postiz_ids=json.dumps({"instagram": "pub-old"}),
            posted_at=datetime(2026, 7, 1, 12, 0, 0),
        )
        resp = client.post(f"/api/content/{row_id}/publish-now")
        assert resp.status_code == 200
        body = resp.json()
        assert body["results"] == []
        assert body["status"] == "posted"
        assert fake_postiz.publish_calls == []
        assert fake_postiz.list_calls == 0  # no Postiz request spent

    def test_fully_published_held_row_click_clears_hold(self, client, repo):
        row_id = seed_row(
            repo,
            status="approved",
            postiz_ids=json.dumps({"instagram": "pub-old"}),
            held_at=datetime(2026, 7, 1, 12, 0, 0),
        )
        resp = client.post(f"/api/content/{row_id}/publish-now")
        assert resp.status_code == 200
        assert get_row(repo, row_id).held_at is None


# --- Failure paths ---


class TestPublishNowFailures:
    def two_platform_row(self, repo, **overrides):
        return seed_row(
            repo,
            platforms=json.dumps({"instagram": True, "facebook": True}),
            captions=json.dumps({"instagram": "IG cap", "facebook": "FB cap"}),
            **overrides,
        )

    def test_partial_failure_reports_real_error_and_holds_row(self, client, repo, fake_postiz):
        fake_postiz.fail_integrations.add("fb-1")
        row_id = self.two_platform_row(repo)
        resp = client.post(f"/api/content/{row_id}/publish-now")
        assert resp.status_code == 200
        body = resp.json()
        by_platform = {r["platform"]: r for r in body["results"]}
        assert by_platform["instagram"]["status"] == "posted"
        assert by_platform["facebook"]["status"] == "failed"
        assert by_platform["facebook"]["error"] == "simulated failure"
        assert body["status"] == "approved"  # not falsely marked published

        row = get_row(repo, row_id)
        assert row.held_at is not None
        assert row.status == "approved"
        assert "failed for facebook: simulated failure" in (row.feedback or "")
        ids = json.loads(row.postiz_ids)
        assert "instagram" in ids
        assert "facebook" not in ids

    def test_manual_continues_past_first_failure(self, client, repo, fake_postiz):
        """Unlike the loop, a manual publish attempts every platform even
        after one fails, so the user sees a result per platform."""
        fake_postiz.fail_integrations.add("fb-1")
        row_id = seed_row(
            repo,
            platforms=json.dumps({"facebook": True, "instagram": True}),
            captions=json.dumps({"facebook": "FB cap", "instagram": "IG cap"}),
        )
        resp = client.post(f"/api/content/{row_id}/publish-now")
        by_platform = {r["platform"]: r for r in resp.json()["results"]}
        assert by_platform["facebook"]["status"] == "failed"
        assert by_platform["instagram"]["status"] == "posted"
        assert len(fake_postiz.publish_calls) == 2

    def test_missing_caption_is_a_per_platform_failure(self, client, repo, fake_postiz):
        row_id = seed_row(
            repo,
            platforms=json.dumps({"instagram": True, "facebook": True}),
            captions=json.dumps({"instagram": "IG cap"}),  # no facebook caption
        )
        resp = client.post(f"/api/content/{row_id}/publish-now")
        by_platform = {r["platform"]: r for r in resp.json()["results"]}
        assert by_platform["facebook"]["status"] == "failed"
        assert by_platform["facebook"]["error"] == "missing caption"
        assert by_platform["instagram"]["status"] == "posted"

    def test_local_only_media_fails_every_platform_and_holds(self, client, repo, fake_postiz):
        row_id = self.two_platform_row(repo, media_url="/media/uploads/x.jpg", alt_text="A cow")
        resp = client.post(f"/api/content/{row_id}/publish-now")
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert [r["status"] for r in results] == ["failed", "failed"]
        assert all("Google Drive" in r["error"] for r in results)
        assert fake_postiz.publish_calls == []
        assert get_row(repo, row_id).held_at is not None

    def test_postiz_integration_listing_error_returns_502(self, client, repo, fake_postiz):
        def boom():
            raise PostizAPIError("postiz down")

        fake_postiz.list_integrations = boom
        row_id = seed_row(repo)
        resp = client.post(f"/api/content/{row_id}/publish-now")
        assert resp.status_code == 502
        assert "postiz down" in resp.json()["detail"]


# --- error_msg exposure (contract W1 item 4) ---


class TestErrorMsgExposure:
    def test_error_msg_null_without_failure_note(self, client, repo):
        row_id = seed_row(repo, feedback="Looks great, ship it")
        resp = client.get(f"/api/content/{row_id}")
        assert resp.json()["error_msg"] is None

    def test_error_msg_populated_after_publish_failure(self, client, repo, fake_postiz):
        fake_postiz.fail_integrations.add("ig-1")
        row_id = seed_row(repo)
        client.post(f"/api/content/{row_id}/publish-now")
        resp = client.get(f"/api/content/{row_id}")
        assert resp.json()["error_msg"] == "instagram: simulated failure"

    def test_postiz_ids_still_exposed(self, client, repo):
        row_id = seed_row(repo, postiz_ids=json.dumps({"instagram": "pub-9"}))
        resp = client.get(f"/api/content/{row_id}")
        assert json.loads(resp.json()["postiz_ids"]) == {"instagram": "pub-9"}


class TestParseLastPublishFailure:
    def test_none_feedback(self):
        assert parse_last_publish_failure(None) is None

    def test_no_failure_lines(self):
        assert parse_last_publish_failure("Nice draft\nplease shorten") is None

    def test_strips_prefix_and_row_held_suffix(self):
        note = "[auto-publish 2026-07-06T12:00:00+00:00] failed for instagram: boom; row held"
        assert parse_last_publish_failure(note) == "instagram: boom"

    def test_last_failure_line_wins(self):
        feedback = "\n".join(
            [
                "[auto-publish 2026-07-01T00:00:00+00:00] failed for instagram: old; row held",
                "user note in between",
                "[auto-publish 2026-07-06T12:00:00+00:00] failed for facebook: new; row held",
            ]
        )
        assert parse_last_publish_failure(feedback) == "facebook: new"

    def test_skip_note_is_not_a_failure(self):
        note = (
            "[auto-publish 2026-07-06T12:00:00+00:00] "
            "no auto-eligible platforms; left for manual release"
        )
        assert parse_last_publish_failure(note) is None


# --- Demo client kwarg parity (contract W1 item 5) ---


class TestDemoPostizClient:
    def test_create_draft_post_accepts_media_and_schedule_kwargs(self):
        from api.demo import DemoPostizClient

        result = DemoPostizClient().create_draft_post(
            "caption", ["demo-ig"], media_url=None, scheduled_at=None
        )
        assert result["id"]

    def test_create_draft_post_positional_still_works(self):
        from api.demo import DemoPostizClient

        assert DemoPostizClient().create_draft_post("caption", ["demo-ig"])["id"]
