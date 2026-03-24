"""Tests for calendar plan view, list, approve, and delete endpoints."""

import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from api.models import Base, CalendarPlan, ContentRow


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


SAMPLE_SLOTS = [
    {
        "date": "2026-03-21",
        "time": "09:00",
        "pillar": "spiritual_education",
        "topic": "Meditation",
        "content_idea": "Morning meditation tips",
        "recommended_media_id": None,
        "target_platforms": ["facebook", "instagram"],
    },
    {
        "date": "2026-03-22",
        "time": "10:00",
        "pillar": "farm_life",
        "topic": "Farm Activities",
        "content_idea": "Spring planting photo tour",
        "recommended_media_id": None,
        "target_platforms": ["instagram"],
    },
    {
        "date": "2026-03-23",
        "time": "14:00",
        "pillar": "events",
        "topic": "Programs",
        "content_idea": "Sunday Love Feast announcement",
        "recommended_media_id": None,
        "target_platforms": ["facebook"],
    },
]


def _seed_plan(engine, status="draft", slots=None):
    with Session(engine) as s:
        plan = CalendarPlan(
            date_range_start=datetime(2026, 3, 21),
            date_range_end=datetime(2026, 3, 27),
            platforms=json.dumps(["facebook", "instagram"]),
            plan_data=json.dumps(slots or SAMPLE_SLOTS),
            status=status,
        )
        s.add(plan)
        s.flush()
        plan_id = plan.id
        s.commit()
    return plan_id


# ── View (GET /api/calendar/plan/{id}) ──────────────────────────────


class TestViewPlan:
    def test_view_returns_plan(self, client, auth_headers, db_engine):
        plan_id = _seed_plan(db_engine)
        resp = client.get(f"/api/calendar/plan/{plan_id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == plan_id
        assert data["status"] == "draft"
        assert len(data["slots"]) == 3

    def test_view_not_found(self, client, auth_headers):
        resp = client.get("/api/calendar/plan/9999", headers=auth_headers)
        assert resp.status_code == 404

    def test_view_includes_slot_details(self, client, auth_headers, db_engine):
        plan_id = _seed_plan(db_engine)
        resp = client.get(f"/api/calendar/plan/{plan_id}", headers=auth_headers)
        slot = resp.json()["slots"][0]
        assert slot["date"] == "2026-03-21"
        assert slot["pillar"] == "spiritual_education"
        assert slot["content_idea"] == "Morning meditation tips"


# ── List (GET /api/calendar/plans) ──────────────────────────────────


class TestListPlans:
    def test_list_returns_plans(self, client, auth_headers, db_engine):
        _seed_plan(db_engine)
        _seed_plan(db_engine, status="approved")
        resp = client.get("/api/calendar/plans", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["plans"]) == 2

    def test_list_filter_by_status(self, client, auth_headers, db_engine):
        _seed_plan(db_engine, status="draft")
        _seed_plan(db_engine, status="approved")
        resp = client.get("/api/calendar/plans?status=draft", headers=auth_headers)
        data = resp.json()
        assert len(data["plans"]) == 1
        assert data["plans"][0]["status"] == "draft"

    def test_list_empty(self, client, auth_headers):
        resp = client.get("/api/calendar/plans", headers=auth_headers)
        data = resp.json()
        assert data["plans"] == []


# ── Approve (POST /api/calendar/plan/{id}/approve) ──────────────────


class TestApprovePlan:
    def test_approve_all_slots(self, client, auth_headers, db_engine):
        plan_id = _seed_plan(db_engine)
        resp = client.post(
            f"/api/calendar/plan/{plan_id}/approve",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["created_count"] == 3
        assert len(data["content_row_ids"]) == 3

        # Verify plan status updated
        with Session(db_engine) as s:
            plan = s.execute(select(CalendarPlan).where(CalendarPlan.id == plan_id)).scalar_one()
            assert plan.status == "approved"

    def test_approve_selected_slots(self, client, auth_headers, db_engine):
        plan_id = _seed_plan(db_engine)
        resp = client.post(
            f"/api/calendar/plan/{plan_id}/approve",
            json={"slot_indices": [0, 2]},
            headers=auth_headers,
        )
        data = resp.json()
        assert data["created_count"] == 2

        # Partial approval
        with Session(db_engine) as s:
            plan = s.execute(select(CalendarPlan).where(CalendarPlan.id == plan_id)).scalar_one()
            assert plan.status == "partial"

    def test_approve_creates_correct_content_rows(self, client, auth_headers, db_engine):
        plan_id = _seed_plan(db_engine)
        resp = client.post(
            f"/api/calendar/plan/{plan_id}/approve",
            json={"slot_indices": [0]},
            headers=auth_headers,
        )
        cr_id = resp.json()["content_row_ids"][0]

        with Session(db_engine) as s:
            row = s.execute(select(ContentRow).where(ContentRow.id == cr_id)).scalar_one()
            assert row.raw_text == "Morning meditation tips"
            assert row.pillar == "spiritual_education"
            assert row.status == "draft"
            assert row.source == "plan"
            platforms = json.loads(row.platforms)
            assert platforms["facebook"] is True
            assert platforms["instagram"] is True

    def test_approve_not_found(self, client, auth_headers):
        resp = client.post(
            "/api/calendar/plan/9999/approve",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_approve_already_approved(self, client, auth_headers, db_engine):
        plan_id = _seed_plan(db_engine, status="approved")
        resp = client.post(
            f"/api/calendar/plan/{plan_id}/approve",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 400


# ── Delete (DELETE /api/calendar/plan/{id}) ─────────────────────────


class TestDeletePlan:
    def test_delete_draft(self, client, auth_headers, db_engine):
        plan_id = _seed_plan(db_engine, status="draft")
        resp = client.delete(f"/api/calendar/plan/{plan_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

    def test_delete_non_draft_rejected(self, client, auth_headers, db_engine):
        plan_id = _seed_plan(db_engine, status="approved")
        resp = client.delete(f"/api/calendar/plan/{plan_id}", headers=auth_headers)
        assert resp.status_code == 400

    def test_delete_not_found(self, client, auth_headers):
        resp = client.delete("/api/calendar/plan/9999", headers=auth_headers)
        assert resp.status_code == 404
