"""Tests for the Phase 1 auto-publish backend.

Covers:
- Eligibility rule matrix (compute_auto_publish_at, no_alt_block)
- hold / resume / require-review / alt-text endpoints
- Approve wiring (sets auto_publish_at; 422 alt_text_required)
- Release loop (publishes due rows, skips held, partial failure holds,
  per-cycle cap) with a fake Postiz client
"""

import asyncio
import json
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.models import Base, ContentRow, PublishConfig
from api.services.auto_publish import (
    acquire_row_claim,
    compute_auto_publish_at,
    no_alt_block,
    release_due_rows,
    release_row_claim,
)
from content_engine.postiz import PostizAPIError

NOW = datetime(2026, 7, 6, 12, 0, 0, tzinfo=UTC)


def make_row(**overrides) -> ContentRow:
    """Build an in-memory ContentRow (not persisted)."""
    defaults = {
        "raw_text": "Cows in the pasture",
        "pillar": "cow_life",
        "status": "approved",
        "platforms": json.dumps({"instagram": True}),
        "captions": json.dumps({"instagram": "IG caption"}),
        "require_review": False,
        "held_at": None,
        "alt_text": None,
        "media_url": None,
        "media_catalog_ids": None,
    }
    defaults.update(overrides)
    return ContentRow(**defaults)


def make_config(platform="instagram", enabled=True, delay_hours=2, pillar_overrides=None):
    return PublishConfig(
        platform=platform,
        enabled=enabled,
        delay_hours=delay_hours,
        pillar_overrides=json.dumps(pillar_overrides) if pillar_overrides is not None else None,
    )


# --- no_alt_block ---


class TestNoAltBlock:
    def test_no_media_is_not_blocked(self):
        assert no_alt_block(make_row()) is False

    def test_media_url_without_alt_is_blocked(self):
        assert no_alt_block(make_row(media_url="https://x.com/a.jpg")) is True

    def test_media_url_with_alt_is_not_blocked(self):
        row = make_row(media_url="https://x.com/a.jpg", alt_text="A brown cow")
        assert no_alt_block(row) is False

    def test_catalog_media_without_alt_is_blocked(self):
        assert no_alt_block(make_row(media_catalog_ids="[1, 2]")) is True

    def test_empty_catalog_list_is_not_blocked(self):
        assert no_alt_block(make_row(media_catalog_ids="[]")) is False

    def test_whitespace_alt_text_is_still_blocked(self):
        row = make_row(media_url="https://x.com/a.jpg", alt_text="   ")
        assert no_alt_block(row) is True


# --- compute_auto_publish_at eligibility matrix ---


class TestComputeAutoPublishAt:
    def test_enabled_platform_returns_now_plus_delay(self):
        result = compute_auto_publish_at(make_row(), [make_config(delay_hours=2)], NOW)
        assert result == NOW + timedelta(hours=2)

    def test_disabled_platform_returns_none(self):
        assert compute_auto_publish_at(make_row(), [make_config(enabled=False)], NOW) is None

    def test_no_config_for_platform_returns_none(self):
        configs = [make_config(platform="facebook")]
        assert compute_auto_publish_at(make_row(), configs, NOW) is None

    def test_pillar_excepted_false_returns_none(self):
        configs = [make_config(pillar_overrides={"cow_life": False})]
        assert compute_auto_publish_at(make_row(), configs, NOW) is None

    def test_pillar_excepted_hold_string_returns_none(self):
        configs = [make_config(pillar_overrides={"cow_life": "hold"})]
        assert compute_auto_publish_at(make_row(), configs, NOW) is None

    def test_pillar_override_true_is_allowed(self):
        configs = [make_config(pillar_overrides={"cow_life": True})]
        assert compute_auto_publish_at(make_row(), configs, NOW) is not None

    def test_other_pillar_excepted_does_not_block(self):
        configs = [make_config(pillar_overrides={"events": False})]
        assert compute_auto_publish_at(make_row(), configs, NOW) is not None

    def test_require_review_returns_none(self):
        row = make_row(require_review=True)
        assert compute_auto_publish_at(row, [make_config()], NOW) is None

    def test_no_alt_block_returns_none(self):
        row = make_row(media_url="https://x.com/a.jpg")
        assert compute_auto_publish_at(row, [make_config()], NOW) is None

    def test_media_with_alt_text_is_eligible(self):
        row = make_row(media_url="https://x.com/a.jpg", alt_text="A cow")
        assert compute_auto_publish_at(row, [make_config()], NOW) is not None

    def test_multiple_platforms_uses_minimum_delay(self):
        row = make_row(platforms=json.dumps({"instagram": True, "facebook": True}))
        configs = [
            make_config(platform="instagram", delay_hours=6),
            make_config(platform="facebook", delay_hours=2),
        ]
        assert compute_auto_publish_at(row, configs, NOW) == NOW + timedelta(hours=2)

    def test_one_eligible_platform_is_enough(self):
        row = make_row(platforms=json.dumps({"instagram": True, "facebook": True}))
        configs = [
            make_config(platform="instagram", enabled=False),
            make_config(platform="facebook", delay_hours=3),
        ]
        assert compute_auto_publish_at(row, configs, NOW) == NOW + timedelta(hours=3)

    def test_no_enabled_platforms_on_row_returns_none(self):
        row = make_row(platforms=json.dumps({"instagram": False}))
        assert compute_auto_publish_at(row, [make_config()], NOW) is None

    def test_row_with_null_pillar_is_allowed(self):
        row = make_row(pillar=None)
        configs = [make_config(pillar_overrides={"cow_life": False})]
        assert compute_auto_publish_at(row, configs, NOW) is not None


# --- API endpoint fixtures (pattern from test_content_endpoints.py) ---


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


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture
def seeded_row_id(repo) -> int:
    """A pending_approval row with one platform."""

    async def seed():
        row = await repo.create_content_row(
            {
                "raw_text": "Morning milking",
                "status": "pending_approval",
                "date": datetime(2026, 7, 1),
                "pillar": "cow_life",
                "platforms": json.dumps({"instagram": True}),
                "captions": json.dumps({"instagram": "IG caption"}),
                "source": "manual",
            }
        )
        return row.id

    return run(seed())


def seed_publish_config(repo, **kwargs):
    async def seed():
        data = {
            "enabled": kwargs.get("enabled", True),
            "delay_hours": kwargs.get("delay_hours", 2),
            "pillar_overrides": json.dumps(kwargs.get("pillar_overrides", {})),
        }
        await repo.upsert_publish_config(platform=kwargs.get("platform", "instagram"), data=data)

    run(seed())


# --- Hold / Resume endpoints ---


class TestHoldResume:
    def test_hold_sets_held_at(self, client, seeded_row_id):
        resp = client.post(f"/api/content/{seeded_row_id}/hold")
        assert resp.status_code == 200
        assert resp.json()["held_at"] is not None

    def test_hold_is_idempotent(self, client, seeded_row_id):
        def parse(value: str) -> datetime:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt

        first = client.post(f"/api/content/{seeded_row_id}/hold").json()["held_at"]
        second = client.post(f"/api/content/{seeded_row_id}/hold").json()["held_at"]
        assert parse(first) == parse(second)

    def test_hold_404(self, client):
        assert client.post("/api/content/999/hold").status_code == 404

    def test_resume_clears_held_at(self, client, seeded_row_id):
        client.post(f"/api/content/{seeded_row_id}/hold")
        resp = client.post(f"/api/content/{seeded_row_id}/resume")
        assert resp.status_code == 200
        assert resp.json()["held_at"] is None

    def test_resume_recomputes_auto_publish_for_approved(
        self, client, repo, db_session, seeded_row_id
    ):
        seed_publish_config(repo)

        async def approve():
            row = await repo.get_content_row(seeded_row_id)
            row.status = "approved"
            await db_session.commit()

        run(approve())
        client.post(f"/api/content/{seeded_row_id}/hold")
        resp = client.post(f"/api/content/{seeded_row_id}/resume")
        assert resp.json()["auto_publish_at"] is not None

    def test_resume_leaves_auto_publish_null_when_ineligible(
        self, client, repo, db_session, seeded_row_id
    ):
        seed_publish_config(repo, enabled=False)

        async def approve():
            row = await repo.get_content_row(seeded_row_id)
            row.status = "approved"
            await db_session.commit()

        run(approve())
        client.post(f"/api/content/{seeded_row_id}/hold")
        resp = client.post(f"/api/content/{seeded_row_id}/resume")
        assert resp.json()["auto_publish_at"] is None

    def test_resume_404(self, client):
        assert client.post("/api/content/999/resume").status_code == 404


# --- Require-review / Alt-text endpoints ---


class TestRequireReviewEndpoint:
    def test_sets_flag(self, client, seeded_row_id):
        resp = client.put(
            f"/api/content/{seeded_row_id}/require-review", json={"require_review": True}
        )
        assert resp.status_code == 200
        assert resp.json()["require_review"] is True

    def test_turning_on_clears_auto_publish_at(self, client, repo, db_session, seeded_row_id):
        async def set_auto():
            row = await repo.get_content_row(seeded_row_id)
            row.auto_publish_at = datetime(2026, 7, 7, tzinfo=UTC)
            await db_session.commit()

        run(set_auto())
        resp = client.put(
            f"/api/content/{seeded_row_id}/require-review", json={"require_review": True}
        )
        assert resp.json()["auto_publish_at"] is None

    def test_turning_off(self, client, seeded_row_id):
        client.put(f"/api/content/{seeded_row_id}/require-review", json={"require_review": True})
        resp = client.put(
            f"/api/content/{seeded_row_id}/require-review", json={"require_review": False}
        )
        assert resp.json()["require_review"] is False

    def test_turning_off_recomputes_auto_publish_for_approved(
        self, client, repo, db_session, seeded_row_id
    ):
        """Regression: review OFF must re-run eligibility, or an approved row
        stays stuck on manual release forever."""
        seed_publish_config(repo)

        async def approve_with_review():
            row = await repo.get_content_row(seeded_row_id)
            row.status = "approved"
            row.require_review = True
            row.auto_publish_at = None
            await db_session.commit()

        run(approve_with_review())
        resp = client.put(
            f"/api/content/{seeded_row_id}/require-review", json={"require_review": False}
        )
        assert resp.json()["auto_publish_at"] is not None

    def test_turning_off_leaves_null_when_still_ineligible(
        self, client, repo, db_session, seeded_row_id
    ):
        seed_publish_config(repo, enabled=False)

        async def approve_with_review():
            row = await repo.get_content_row(seeded_row_id)
            row.status = "approved"
            row.require_review = True
            await db_session.commit()

        run(approve_with_review())
        resp = client.put(
            f"/api/content/{seeded_row_id}/require-review", json={"require_review": False}
        )
        assert resp.json()["auto_publish_at"] is None

    def test_turning_off_does_not_set_auto_publish_for_non_approved(
        self, client, repo, seeded_row_id
    ):
        seed_publish_config(repo)
        client.put(f"/api/content/{seeded_row_id}/require-review", json={"require_review": True})
        resp = client.put(
            f"/api/content/{seeded_row_id}/require-review", json={"require_review": False}
        )
        # Row is still pending_approval; approve computes it later.
        assert resp.json()["auto_publish_at"] is None

    def test_404(self, client):
        resp = client.put("/api/content/999/require-review", json={"require_review": True})
        assert resp.status_code == 404


class TestAltTextEndpoint:
    def test_sets_alt_text(self, client, seeded_row_id):
        resp = client.put(
            f"/api/content/{seeded_row_id}/alt-text", json={"alt_text": "A cow at sunrise"}
        )
        assert resp.status_code == 200
        assert resp.json()["alt_text"] == "A cow at sunrise"

    def test_persists(self, client, repo, seeded_row_id):
        client.put(f"/api/content/{seeded_row_id}/alt-text", json={"alt_text": "Barn photo"})
        row = run(repo.get_content_row(seeded_row_id))
        assert row.alt_text == "Barn photo"

    def test_404(self, client):
        resp = client.put("/api/content/999/alt-text", json={"alt_text": "x"})
        assert resp.status_code == 404

    def test_alt_text_recomputes_auto_publish_for_approved_row(
        self, client, repo, db_session, seeded_row_id
    ):
        """Regression: fixing alt text must clear the NO-ALT block by
        recomputing auto_publish_at, otherwise the approved row never
        auto-releases."""
        seed_publish_config(repo)

        async def approve_with_media():
            row = await repo.get_content_row(seeded_row_id)
            row.status = "approved"
            row.media_url = "https://x.com/a.jpg"
            row.auto_publish_at = None  # blocked at approve time (no alt)
            await db_session.commit()

        run(approve_with_media())
        resp = client.put(
            f"/api/content/{seeded_row_id}/alt-text", json={"alt_text": "A brown cow"}
        )
        assert resp.status_code == 200
        assert resp.json()["auto_publish_at"] is not None

    def test_alt_text_leaves_null_when_config_ineligible(
        self, client, repo, db_session, seeded_row_id
    ):
        seed_publish_config(repo, enabled=False)

        async def approve_with_media():
            row = await repo.get_content_row(seeded_row_id)
            row.status = "approved"
            row.media_url = "https://x.com/a.jpg"
            await db_session.commit()

        run(approve_with_media())
        resp = client.put(f"/api/content/{seeded_row_id}/alt-text", json={"alt_text": "A cow"})
        assert resp.json()["auto_publish_at"] is None

    def test_alt_text_does_not_touch_non_approved_rows(self, client, repo, seeded_row_id):
        seed_publish_config(repo)
        resp = client.put(f"/api/content/{seeded_row_id}/alt-text", json={"alt_text": "A cow"})
        assert resp.json()["auto_publish_at"] is None


# --- Approve wiring ---


@pytest.fixture
def mock_postiz(client):
    from unittest.mock import MagicMock

    from api.dependencies import get_postiz_client
    from api.main import app

    mock = MagicMock()
    mock.list_integrations.return_value = [
        {"id": "ig-1", "identifier": "instagram", "name": "IG"},
    ]
    mock.create_draft_post.return_value = {"id": "draft-123"}
    app.dependency_overrides[get_postiz_client] = lambda: mock
    return mock


class TestApproveAutoPublish:
    def test_approve_sets_auto_publish_at_when_eligible(
        self, client, repo, seeded_row_id, mock_postiz
    ):
        seed_publish_config(repo, delay_hours=2)
        resp = client.post(f"/api/drafts/{seeded_row_id}/approve")
        assert resp.status_code == 200
        row = run(repo.get_content_row(seeded_row_id))
        assert row.auto_publish_at is not None

    def test_approve_leaves_null_when_config_disabled(
        self, client, repo, seeded_row_id, mock_postiz
    ):
        seed_publish_config(repo, enabled=False)
        client.post(f"/api/drafts/{seeded_row_id}/approve")
        row = run(repo.get_content_row(seeded_row_id))
        assert row.auto_publish_at is None

    def test_approve_leaves_null_when_pillar_excepted(
        self, client, repo, seeded_row_id, mock_postiz
    ):
        seed_publish_config(repo, pillar_overrides={"cow_life": False})
        client.post(f"/api/drafts/{seeded_row_id}/approve")
        row = run(repo.get_content_row(seeded_row_id))
        assert row.auto_publish_at is None

    def test_approve_leaves_null_when_no_alt(
        self, client, repo, db_session, seeded_row_id, mock_postiz
    ):
        seed_publish_config(repo)

        async def add_media():
            row = await repo.get_content_row(seeded_row_id)
            row.media_url = "https://x.com/a.jpg"
            await db_session.commit()

        run(add_media())
        client.post(f"/api/drafts/{seeded_row_id}/approve")
        row = run(repo.get_content_row(seeded_row_id))
        assert row.auto_publish_at is None

    def test_approve_with_schedule_and_no_alt_returns_422(
        self, client, repo, db_session, seeded_row_id, mock_postiz
    ):
        async def add_media():
            row = await repo.get_content_row(seeded_row_id)
            row.media_url = "https://x.com/a.jpg"
            await db_session.commit()

        run(add_media())
        resp = client.post(f"/api/drafts/{seeded_row_id}/approve?schedule=true")
        assert resp.status_code == 422
        assert resp.json()["detail"] == "alt_text_required"
        # Row was NOT approved
        row = run(repo.get_content_row(seeded_row_id))
        assert row.status == "pending_approval"

    def test_saving_draft_with_media_and_no_alt_is_allowed(
        self, client, repo, db_session, seeded_row_id
    ):
        async def add_media():
            row = await repo.get_content_row(seeded_row_id)
            row.media_url = "https://x.com/a.jpg"
            await db_session.commit()

        run(add_media())
        resp = client.post(
            f"/api/drafts/{seeded_row_id}/edit",
            json={"captions": {"instagram": "edited"}},
        )
        assert resp.status_code == 200


# --- Release loop ---


@pytest.fixture(autouse=True)
def _reset_request_budget():
    """The rolling request window is module-level state; isolate tests."""
    from api.services import auto_publish

    auto_publish._request_times.clear()
    yield
    auto_publish._request_times.clear()


@pytest.fixture(autouse=True)
def _reset_row_claims():
    """In-flight row claims are module-level state; isolate tests."""
    from api.services import auto_publish

    auto_publish._in_flight_rows.clear()
    yield
    auto_publish._in_flight_rows.clear()


@pytest_asyncio.fixture
async def release_configs(repo):
    """Enabled publish configs for both fake integrations (release-time
    eligibility requires a config; without one a platform is skipped)."""
    for platform in ("instagram", "facebook"):
        await repo.upsert_publish_config(
            platform=platform,
            data={"enabled": True, "delay_hours": 2, "pillar_overrides": "{}"},
        )


class FakePostiz:
    """Fake Postiz client for release-loop tests."""

    INTEGRATIONS = [
        {"id": "ig-1", "identifier": "instagram", "name": "IG"},
        {"id": "fb-1", "identifier": "facebook", "name": "FB"},
    ]

    def __init__(self, fail_integrations=None):
        self.fail_integrations = set(fail_integrations or [])
        self.publish_calls = []
        self._counter = 0

    def list_integrations(self):
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
        return {"id": f"pub-{self._counter}"}


async def seed_due_row(repo, **overrides):
    data = {
        "raw_text": "Due content",
        "status": "approved",
        "date": datetime(2026, 7, 1),
        "pillar": "cow_life",
        "platforms": json.dumps({"instagram": True}),
        "captions": json.dumps({"instagram": "IG caption"}),
        "auto_publish_at": NOW - timedelta(minutes=5),
        "source": "manual",
    }
    data.update(overrides)
    return await repo.create_content_row(data)


@pytest.mark.asyncio
class TestReleaseLoop:
    async def test_publishes_due_row(self, db_session, repo, release_configs):
        row = await seed_due_row(repo)
        fake = FakePostiz()

        summary = await release_due_rows(db_session, NOW, fake)

        assert summary["published"] == 1
        updated = await repo.get_content_row(row.id)
        assert updated.status == "posted"
        assert updated.posted_at is not None
        assert json.loads(updated.postiz_ids) == {"instagram": "pub-1"}
        assert len(fake.publish_calls) == 1

    async def test_one_post_per_platform(self, db_session, repo, release_configs):
        row = await seed_due_row(
            repo,
            platforms=json.dumps({"instagram": True, "facebook": True}),
            captions=json.dumps({"instagram": "IG cap", "facebook": "FB cap"}),
        )
        fake = FakePostiz()

        await release_due_rows(db_session, NOW, fake)

        assert len(fake.publish_calls) == 2
        updated = await repo.get_content_row(row.id)
        ids = json.loads(updated.postiz_ids)
        assert set(ids.keys()) == {"instagram", "facebook"}

    async def test_future_dated_row_is_scheduled(self, db_session, repo, release_configs):
        future = NOW + timedelta(days=2)
        row = await seed_due_row(repo, date=future)
        fake = FakePostiz()

        await release_due_rows(db_session, NOW, fake)

        updated = await repo.get_content_row(row.id)
        assert updated.status == "scheduled"
        assert updated.posted_at is None
        assert fake.publish_calls[0]["scheduled_at"] is not None

    async def test_skips_held_rows(self, db_session, repo, release_configs):
        await seed_due_row(repo, held_at=NOW - timedelta(hours=1))
        fake = FakePostiz()

        summary = await release_due_rows(db_session, NOW, fake)

        assert summary == {"published": 0, "held": 0, "deferred": 0, "skipped": 0}
        assert fake.publish_calls == []

    async def test_skips_not_yet_due_rows(self, db_session, repo, release_configs):
        await seed_due_row(repo, auto_publish_at=NOW + timedelta(hours=1))
        fake = FakePostiz()

        summary = await release_due_rows(db_session, NOW, fake)
        assert summary["published"] == 0
        assert fake.publish_calls == []

    async def test_skips_non_approved_rows(self, db_session, repo, release_configs):
        await seed_due_row(repo, status="draft")
        await seed_due_row(repo, status="posted")
        fake = FakePostiz()

        summary = await release_due_rows(db_session, NOW, fake)
        assert summary["published"] == 0

    async def test_skips_rows_without_auto_publish_at(self, db_session, repo, release_configs):
        await seed_due_row(repo, auto_publish_at=None)
        fake = FakePostiz()

        summary = await release_due_rows(db_session, NOW, fake)
        assert summary["published"] == 0

    async def test_partial_failure_holds_row(self, db_session, repo, release_configs):
        row = await seed_due_row(
            repo,
            platforms=json.dumps({"instagram": True, "facebook": True}),
            captions=json.dumps({"instagram": "IG cap", "facebook": "FB cap"}),
        )
        fake = FakePostiz(fail_integrations={"fb-1"})

        summary = await release_due_rows(db_session, NOW, fake)

        assert summary["held"] == 1
        updated = await repo.get_content_row(row.id)
        assert updated.held_at is not None
        assert updated.status == "approved"  # not falsely marked published
        assert "facebook" in (updated.feedback or "")
        ids = json.loads(updated.postiz_ids)
        assert "instagram" in ids  # successful platform is recorded
        assert "facebook" not in ids

    async def test_respects_per_cycle_cap(self, db_session, repo, release_configs):
        for _ in range(7):
            await seed_due_row(repo)
        fake = FakePostiz()

        summary = await release_due_rows(db_session, NOW, fake, max_rows=5)

        assert summary["published"] == 5
        assert summary["deferred"] == 2
        assert len(fake.publish_calls) == 5


# --- Release-time eligibility split (regression: bug #1) ---


@pytest.mark.asyncio
class TestReleaseEligibilitySplit:
    async def seed_configs(self, repo, fb_enabled=True, fb_pillar_overrides=None):
        await repo.upsert_publish_config(
            platform="instagram",
            data={"enabled": True, "delay_hours": 2, "pillar_overrides": "{}"},
        )
        await repo.upsert_publish_config(
            platform="facebook",
            data={
                "enabled": fb_enabled,
                "delay_hours": 2,
                "pillar_overrides": json.dumps(fb_pillar_overrides or {}),
            },
        )

    async def test_disabled_platform_is_skipped_not_force_published(self, db_session, repo):
        """A disabled platform with caption+integration must NOT publish when
        another platform's timer fires."""
        await self.seed_configs(repo, fb_enabled=False)
        row = await seed_due_row(
            repo,
            platforms=json.dumps({"instagram": True, "facebook": True}),
            captions=json.dumps({"instagram": "IG cap", "facebook": "FB cap"}),
        )
        fake = FakePostiz()

        summary = await release_due_rows(db_session, NOW, fake)

        assert summary["published"] == 1
        assert [c["platform_ids"] for c in fake.publish_calls] == [["ig-1"]]
        updated = await repo.get_content_row(row.id)
        assert updated.held_at is None
        ids = json.loads(updated.postiz_ids)
        assert "instagram" in ids
        assert "facebook" not in ids  # stays pending for manual release

    async def test_pillar_held_platform_is_skipped(self, db_session, repo):
        await self.seed_configs(repo, fb_pillar_overrides={"cow_life": False})
        row = await seed_due_row(
            repo,
            platforms=json.dumps({"instagram": True, "facebook": True}),
            captions=json.dumps({"instagram": "IG cap", "facebook": "FB cap"}),
        )
        fake = FakePostiz()

        await release_due_rows(db_session, NOW, fake)

        updated = await repo.get_content_row(row.id)
        ids = json.loads(updated.postiz_ids)
        assert "facebook" not in ids
        assert [c["platform_ids"] for c in fake.publish_calls] == [["ig-1"]]

    async def test_ineligible_platform_without_caption_does_not_hold_row(self, db_session, repo):
        """An ineligible platform missing caption/integration must not count
        as a failure and must not block the eligible platform."""
        await self.seed_configs(repo, fb_enabled=False)
        row = await seed_due_row(
            repo,
            platforms=json.dumps({"facebook": True, "instagram": True}),
            captions=json.dumps({"instagram": "IG cap"}),  # no facebook caption
        )
        fake = FakePostiz()

        summary = await release_due_rows(db_session, NOW, fake)

        assert summary["published"] == 1
        assert summary["held"] == 0
        updated = await repo.get_content_row(row.id)
        assert updated.held_at is None
        assert updated.status == "posted"
        assert "instagram" in json.loads(updated.postiz_ids)

    async def test_all_ineligible_row_returns_to_manual_release(self, db_session, repo):
        await self.seed_configs(repo, fb_enabled=False)
        row = await seed_due_row(
            repo,
            platforms=json.dumps({"facebook": True}),
            captions=json.dumps({"facebook": "FB cap"}),
        )
        fake = FakePostiz()

        summary = await release_due_rows(db_session, NOW, fake)

        assert summary["skipped"] == 1
        assert summary["published"] == 0
        assert summary["held"] == 0
        assert fake.publish_calls == []
        updated = await repo.get_content_row(row.id)
        assert updated.status == "approved"
        assert updated.held_at is None
        assert updated.auto_publish_at is None  # not re-selected every cycle
        assert "manual release" in (updated.feedback or "")

    async def test_eligible_platform_missing_caption_still_holds_row(self, db_session, repo):
        """Real problems on ELIGIBLE platforms remain a partial-failure hold."""
        await self.seed_configs(repo)
        row = await seed_due_row(
            repo,
            platforms=json.dumps({"instagram": True}),
            captions=json.dumps({}),
        )
        fake = FakePostiz()

        summary = await release_due_rows(db_session, NOW, fake)

        assert summary["held"] == 1
        updated = await repo.get_content_row(row.id)
        assert updated.held_at is not None


# --- Per-row commit (regression: bug #2, crash between rows double-posts) ---


class CrashError(BaseException):
    """Simulates a process crash: not caught by `except Exception`."""


class CrashingPostiz(FakePostiz):
    """Publishes normally, then 'crashes the process' after N publishes."""

    def __init__(self, crash_after: int):
        super().__init__()
        self.crash_after = crash_after

    def publish_post(self, *args, **kwargs):
        if len(self.publish_calls) >= self.crash_after:
            raise CrashError("simulated crash")
        return super().publish_post(*args, **kwargs)


@pytest.mark.asyncio
class TestPerRowCommit:
    async def test_crash_between_rows_persists_first_row_state(
        self, db_session, repo, release_configs
    ):
        row1 = await seed_due_row(repo, auto_publish_at=NOW - timedelta(minutes=10))
        row2 = await seed_due_row(repo, auto_publish_at=NOW - timedelta(minutes=5))
        fake = CrashingPostiz(crash_after=1)

        with pytest.raises(CrashError):
            await release_due_rows(db_session, NOW, fake)

        # Discard anything not committed — the crash means it never persisted.
        await db_session.rollback()

        first = await repo.get_content_row(row1.id)
        assert first.status == "posted"  # committed before the crash
        assert json.loads(first.postiz_ids) == {"instagram": "pub-1"}
        second = await repo.get_content_row(row2.id)
        assert second.status == "approved"  # untouched, will retry next cycle


# --- Request budget (regression: bug #3, 30 req/hour Postiz limit) ---


@pytest.mark.asyncio
class TestRequestBudget:
    async def test_budget_defers_extra_rows(self, db_session, repo, release_configs):
        row1 = await seed_due_row(repo, auto_publish_at=NOW - timedelta(minutes=10))
        row2 = await seed_due_row(repo, auto_publish_at=NOW - timedelta(minutes=5))
        fake = FakePostiz()

        summary = await release_due_rows(db_session, NOW, fake, request_budget=1)

        assert summary["published"] == 1
        assert summary["deferred"] == 1
        assert len(fake.publish_calls) == 1
        first = await repo.get_content_row(row1.id)
        assert first.status == "posted"
        second = await repo.get_content_row(row2.id)
        assert second.status == "approved"
        assert second.auto_publish_at is not None  # retried next cycle

    async def test_budget_exhausted_mid_row_defers_without_hold(
        self, db_session, repo, release_configs
    ):
        row = await seed_due_row(
            repo,
            platforms=json.dumps({"instagram": True, "facebook": True}),
            captions=json.dumps({"instagram": "IG cap", "facebook": "FB cap"}),
        )
        fake = FakePostiz()

        summary = await release_due_rows(db_session, NOW, fake, request_budget=1)

        assert summary["deferred"] == 1
        assert summary["held"] == 0
        assert len(fake.publish_calls) == 1
        updated = await repo.get_content_row(row.id)
        assert updated.status == "approved"  # not marked posted
        assert updated.held_at is None
        assert updated.auto_publish_at is not None
        # The published platform is persisted so the next cycle won't repeat it.
        assert "instagram" in json.loads(updated.postiz_ids)

    async def test_publishes_across_cycles_resume_pending_platforms(
        self, db_session, repo, release_configs
    ):
        row = await seed_due_row(
            repo,
            platforms=json.dumps({"instagram": True, "facebook": True}),
            captions=json.dumps({"instagram": "IG cap", "facebook": "FB cap"}),
        )
        fake = FakePostiz()

        await release_due_rows(db_session, NOW, fake, request_budget=1)
        # Next cycle, one hour later: window rolled over, budget available.
        later = NOW + timedelta(hours=1, minutes=1)
        summary = await release_due_rows(db_session, later, fake, request_budget=1)

        assert summary["published"] == 1
        updated = await repo.get_content_row(row.id)
        assert updated.status == "posted"
        ids = json.loads(updated.postiz_ids)
        assert set(ids.keys()) == {"instagram", "facebook"}
        assert len(fake.publish_calls) == 2  # instagram was never re-published


# --- Row claim (regression: B1, loop vs publish-now double-publish race) ---


@pytest.mark.asyncio
class TestRowClaim:
    async def test_acquire_blocks_second_acquire_until_released(self):
        assert await acquire_row_claim(1) is True
        assert await acquire_row_claim(1) is False  # already in flight
        assert await acquire_row_claim(2) is True  # other rows unaffected
        await release_row_claim(1)
        assert await acquire_row_claim(1) is True

    async def test_release_unclaimed_row_is_safe(self):
        await release_row_claim(999)  # must not raise

    async def test_loop_skips_claimed_row_and_picks_it_up_next_cycle(
        self, db_session, repo, release_configs
    ):
        row = await seed_due_row(repo)
        fake = FakePostiz()

        assert await acquire_row_claim(row.id)  # e.g. publish-now is mid-flight
        try:
            summary = await release_due_rows(db_session, NOW, fake)
        finally:
            await release_row_claim(row.id)

        # Claimed row skipped: nothing published, row untouched.
        assert fake.publish_calls == []
        assert summary["published"] == 0
        assert summary["deferred"] == 1
        untouched = await repo.get_content_row(row.id)
        assert untouched.status == "approved"
        assert untouched.auto_publish_at is not None
        assert untouched.postiz_ids is None

        # Next cycle (claim released) picks the row up.
        summary = await release_due_rows(db_session, NOW, fake)
        assert summary["published"] == 1
        assert len(fake.publish_calls) == 1

    async def test_loop_releases_claims_after_cycle(self, db_session, repo, release_configs):
        from api.services import auto_publish

        await seed_due_row(repo)
        summary = await release_due_rows(db_session, NOW, FakePostiz())
        assert summary["published"] == 1
        assert auto_publish._in_flight_rows == set()

    async def test_loop_releases_claim_on_publish_crash(self, db_session, repo, release_configs):
        """The claim must be released on ANY exit path (try/finally), even a
        crash-level BaseException escaping the publish core."""
        from api.services import auto_publish

        await seed_due_row(repo)
        fake = CrashingPostiz(crash_after=0)

        with pytest.raises(CrashError):
            await release_due_rows(db_session, NOW, fake)
        assert auto_publish._in_flight_rows == set()


# --- Pillar response contract ---


class TestPillarTargetField:
    def test_pillar_includes_target_percent(self, client, db_session):
        from api.models import Pillar

        async def seed():
            db_session.add(Pillar(name="cow_life", color="#8fbf6b", target_distribution=0.4))
            await db_session.commit()

        run(seed())
        resp = client.get("/api/pillars")
        assert resp.status_code == 200
        item = resp.json()[0]
        assert item["color"] == "#8fbf6b"
        assert item["target"] == 40

    def test_pillar_target_null_when_unset(self, client, db_session):
        from api.models import Pillar

        async def seed():
            db_session.add(Pillar(name="events"))
            await db_session.commit()

        run(seed())
        resp = client.get("/api/pillars")
        assert resp.json()[0]["target"] is None
