"""Integration tests for Phase 3 end-to-end workflows.

Tests complete user flows: upload → browse → suggest → attach → adapt → plan.
All external services (Claude CLI, Postiz, Drive) are mocked.
"""

import io
import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from api.models import (
    Base,
    CalendarPlan,
    ContentRow,
    Pillar,
)


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


def _make_test_image(width=800, height=600) -> io.BytesIO:
    img = Image.new("RGB", (width, height), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf


def _seed_pillars(engine):
    with Session(engine) as s:
        for name, weight in [
            ("spiritual_education", 0.4),
            ("farm_life", 0.25),
            ("events", 0.15),
        ]:
            s.add(Pillar(name=name, target_distribution=weight, is_active=True))
        s.commit()


class TestMediaUploadFlow:
    """Upload → browse → detail → tag → delete."""

    @patch("api.routes.media._generate_media_meta")
    @patch("api.routes.media._upload_to_postiz")
    def test_full_media_lifecycle(self, mock_postiz, mock_tags, client, auth_headers):
        mock_postiz.return_value = None
        mock_tags.return_value = {
            "alt_text": "Cows grazing in a farm pasture",
            "season": None,
            "tags": [
                {"tag": "cows", "confidence": 0.95},
                {"tag": "farm", "confidence": 0.8},
            ],
        }

        # 1. Upload
        img = _make_test_image()
        resp = client.post(
            "/api/media/upload",
            files={"file": ("cow-photo.jpg", img, "image/jpeg")},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        media_id = resp.json()["id"]

        # 2. Browse — should find the uploaded media
        resp = client.get("/api/media", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["id"] == media_id

        # 3. Detail — should include tags
        resp = client.get(f"/api/media/{media_id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["tags"]) == 2

        # 4. Add manual tag
        resp = client.put(
            f"/api/media/{media_id}/tags",
            json={"add": ["pastoral"], "remove": []},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()["tags"]) == 3

        # 5. Delete
        resp = client.delete(f"/api/media/{media_id}", headers=auth_headers)
        assert resp.status_code == 200

        # 6. Verify gone
        resp = client.get(f"/api/media/{media_id}", headers=auth_headers)
        assert resp.status_code == 404


class TestMediaSuggestionFlow:
    """Create content → get suggestions → attach media."""

    @patch("api.routes.media._generate_media_meta")
    @patch("api.routes.media._upload_to_postiz")
    def test_suggest_and_attach(self, mock_postiz, mock_tags, client, auth_headers, db_engine):
        mock_postiz.return_value = None
        mock_tags.return_value = {
            "alt_text": "A farm scene",
            "season": None,
            "tags": [{"tag": "farm", "confidence": 0.9}],
        }

        # 1. Upload media with farm tag
        img = _make_test_image()
        resp = client.post(
            "/api/media/upload",
            files={"file": ("farm.jpg", img, "image/jpeg")},
            headers=auth_headers,
        )
        media_id = resp.json()["id"]

        # 2. Create a content row about farming
        with Session(db_engine) as s:
            row = ContentRow(
                raw_text="Beautiful farm day with cows grazing",
                pillar="farm_life",
                status="draft",
                platforms=json.dumps({"facebook": True}),
                captions=json.dumps({}),
            )
            s.add(row)
            s.flush()
            cr_id = row.id
            s.commit()

        # 3. Get suggestions — farm media should be suggested
        resp = client.get(
            f"/api/media/suggest?content_row_id={cr_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        suggestions = resp.json()["suggestions"]
        assert len(suggestions) >= 1
        assert suggestions[0]["media_id"] == media_id

        # 4. Attach the suggested media
        resp = client.put(
            f"/api/content/{cr_id}/attach-media?media_id={media_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert media_id in resp.json()["media_catalog_ids"]


class TestCalendarPlanningFlow:
    """Plan → review → approve → verify drafts created."""

    @patch("api.routes.calendar_plan._run_claude")
    def test_plan_and_approve(self, mock_claude, client, auth_headers, db_engine):
        _seed_pillars(db_engine)

        mock_claude.return_value = json.dumps(
            [
                {
                    "date": "2026-04-01",
                    "time": "09:00",
                    "pillar": "spiritual_education",
                    "topic": "Meditation",
                    "content_idea": "Morning meditation guide",
                    "recommended_media_id": None,
                    "target_platforms": ["facebook", "instagram"],
                },
                {
                    "date": "2026-04-02",
                    "time": "10:00",
                    "pillar": "farm_life",
                    "topic": "Farm",
                    "content_idea": "Spring planting update",
                    "recommended_media_id": None,
                    "target_platforms": ["instagram"],
                },
            ]
        )

        # 1. Create plan
        resp = client.post(
            "/api/calendar/plan",
            json={
                "date_range_start": "2026-04-01",
                "date_range_end": "2026-04-07",
                "platforms": ["facebook", "instagram"],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        plan_id = resp.json()["id"]
        assert resp.json()["status"] == "draft"
        assert len(resp.json()["slots"]) == 2

        # 2. View plan
        resp = client.get(f"/api/calendar/plan/{plan_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["slots"][0]["content_idea"] == "Morning meditation guide"

        # 3. Approve all slots
        resp = client.post(
            f"/api/calendar/plan/{plan_id}/approve",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["created_count"] == 2

        # 4. Verify content rows created
        cr_ids = resp.json()["content_row_ids"]
        with Session(db_engine) as s:
            for cr_id in cr_ids:
                row = s.get(ContentRow, cr_id)
                assert row is not None
                assert row.status == "draft"
                assert row.source == "plan"

        # 5. Plan should be approved
        with Session(db_engine) as s:
            plan = s.get(CalendarPlan, plan_id)
            assert plan.status == "approved"

        # 6. Can't re-approve
        resp = client.post(
            f"/api/calendar/plan/{plan_id}/approve",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 400


class TestMediaAdaptationFlow:
    """Upload → adapt → verify dimensions."""

    @patch("api.routes.media._generate_media_meta")
    @patch("api.routes.media._upload_to_postiz")
    def test_upload_and_adapt(self, mock_postiz, mock_tags, client, auth_headers):
        mock_postiz.return_value = None
        mock_tags.return_value = {"alt_text": "A landscape", "season": None, "tags": []}

        # 1. Upload a landscape image
        img = _make_test_image(1920, 1080)
        resp = client.post(
            "/api/media/upload",
            files={"file": ("landscape.jpg", img, "image/jpeg")},
            headers=auth_headers,
        )
        media_id = resp.json()["id"]

        # 2. Adapt for multiple platforms
        resp = client.post(
            f"/api/media/{media_id}/adapt",
            json={
                "platforms": ["instagram", "facebook"],
                "formats": ["post", "story"],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        adapted = resp.json()["adapted"]

        # Should have: IG post, IG story, FB post, FB story = 4
        assert len(adapted) == 4

        # Verify dimensions
        ig_post = next(a for a in adapted if a["platform"] == "instagram" and a["format"] == "post")
        assert ig_post["width"] == 1080
        assert ig_post["height"] == 1080

        fb_post = next(a for a in adapted if a["platform"] == "facebook" and a["format"] == "post")
        assert fb_post["width"] == 1200
        assert fb_post["height"] == 630


class TestFilterAndSearchFlow:
    """Upload multiple → filter by source, pillar, tag."""

    @patch("api.routes.media._generate_media_meta")
    @patch("api.routes.media._upload_to_postiz")
    def test_filters_work_end_to_end(self, mock_postiz, mock_tags, client, auth_headers, db_engine):
        mock_postiz.return_value = None

        # Upload 1: farm tag
        mock_tags.return_value = {
            "alt_text": "A farm scene",
            "season": None,
            "tags": [{"tag": "farm", "confidence": 0.9}],
        }
        img1 = _make_test_image()
        client.post(
            "/api/media/upload",
            files={"file": ("farm.jpg", img1, "image/jpeg")},
            headers=auth_headers,
        )

        # Upload 2: temple tag
        mock_tags.return_value = {
            "alt_text": "A temple building",
            "season": None,
            "tags": [{"tag": "temple", "confidence": 0.9}],
        }
        img2 = _make_test_image()
        client.post(
            "/api/media/upload",
            files={"file": ("temple.jpg", img2, "image/jpeg")},
            headers=auth_headers,
        )

        # Browse all — should see 2
        resp = client.get("/api/media", headers=auth_headers)
        assert resp.json()["total"] == 2

        # Filter by tag
        resp = client.get("/api/media?tag=farm", headers=auth_headers)
        assert resp.json()["total"] == 1

        resp = client.get("/api/media?tag=temple", headers=auth_headers)
        assert resp.json()["total"] == 1

        # Filter by source
        resp = client.get("/api/media?source=upload", headers=auth_headers)
        assert resp.json()["total"] == 2
