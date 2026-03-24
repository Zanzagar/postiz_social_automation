"""Tests for AI calendar planning endpoint."""

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from api.models import Base, CalendarPlan, Pillar, WebKnowledge


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


def _seed_pillars(engine):
    with Session(engine) as s:
        for name, weight in [
            ("spiritual_education", 0.4),
            ("farm_life", 0.25),
            ("events", 0.15),
            ("behind_the_scenes", 0.1),
            ("seasonal", 0.05),
            ("collaborative", 0.05),
        ]:
            s.add(Pillar(name=name, target_distribution=weight, is_active=True))
        s.commit()


def _seed_knowledge(engine):
    with Session(engine) as s:
        s.add(
            WebKnowledge(
                fact_type="program",
                content="Sunday Love Feast program at Gita Valley",
                topic="Programs",
                pillar="events",
            )
        )
        s.commit()


MOCK_CLAUDE_RESPONSE = json.dumps(
    [
        {
            "date": "2026-03-21",
            "time": "09:00",
            "pillar": "spiritual_education",
            "topic": "Spiritual Life",
            "content_idea": "Share morning meditation tips for busy professionals",
            "recommended_media_id": None,
            "target_platforms": ["facebook", "instagram"],
        },
        {
            "date": "2026-03-22",
            "time": "10:00",
            "pillar": "farm_life",
            "topic": "Farm Activities",
            "content_idea": "Photo tour of spring planting at Gita Valley",
            "recommended_media_id": None,
            "target_platforms": ["instagram"],
        },
    ]
)


class TestCalendarPlan:
    @patch("api.routes.calendar_plan._run_claude")
    def test_creates_plan(self, mock_claude, client, auth_headers, db_engine):
        mock_claude.return_value = MOCK_CLAUDE_RESPONSE
        _seed_pillars(db_engine)

        resp = client.post(
            "/api/calendar/plan",
            json={
                "date_range_start": "2026-03-21",
                "date_range_end": "2026-03-27",
                "platforms": ["facebook", "instagram"],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] is not None
        assert data["status"] == "draft"
        assert len(data["slots"]) == 2

    @patch("api.routes.calendar_plan._run_claude")
    def test_saves_to_database(self, mock_claude, client, auth_headers, db_engine):
        mock_claude.return_value = MOCK_CLAUDE_RESPONSE
        _seed_pillars(db_engine)

        resp = client.post(
            "/api/calendar/plan",
            json={
                "date_range_start": "2026-03-21",
                "date_range_end": "2026-03-27",
                "platforms": ["facebook"],
            },
            headers=auth_headers,
        )
        plan_id = resp.json()["id"]

        with Session(db_engine) as s:
            plan = s.execute(select(CalendarPlan).where(CalendarPlan.id == plan_id)).scalar_one()
            assert plan.status == "draft"
            assert plan.plan_data is not None

    @patch("api.routes.calendar_plan._run_claude")
    def test_incorporates_pillars_in_prompt(self, mock_claude, client, auth_headers, db_engine):
        mock_claude.return_value = MOCK_CLAUDE_RESPONSE
        _seed_pillars(db_engine)

        client.post(
            "/api/calendar/plan",
            json={
                "date_range_start": "2026-03-21",
                "date_range_end": "2026-03-27",
                "platforms": ["facebook"],
            },
            headers=auth_headers,
        )
        # Verify Claude was called with a prompt containing pillar info
        prompt = mock_claude.call_args[0][0]
        assert "spiritual_education" in prompt
        assert "40%" in prompt or "0.4" in prompt

    @patch("api.routes.calendar_plan._run_claude")
    def test_incorporates_knowledge(self, mock_claude, client, auth_headers, db_engine):
        mock_claude.return_value = MOCK_CLAUDE_RESPONSE
        _seed_pillars(db_engine)
        _seed_knowledge(db_engine)

        client.post(
            "/api/calendar/plan",
            json={
                "date_range_start": "2026-03-21",
                "date_range_end": "2026-03-27",
                "platforms": ["facebook"],
            },
            headers=auth_headers,
        )
        prompt = mock_claude.call_args[0][0]
        assert "Sunday Love Feast" in prompt

    @patch("api.routes.calendar_plan._run_claude")
    def test_claude_failure_returns_error(self, mock_claude, client, auth_headers, db_engine):
        mock_claude.side_effect = RuntimeError("Claude CLI not available")
        _seed_pillars(db_engine)

        resp = client.post(
            "/api/calendar/plan",
            json={
                "date_range_start": "2026-03-21",
                "date_range_end": "2026-03-27",
                "platforms": ["facebook"],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 500

    def test_invalid_date_range(self, client, auth_headers):
        resp = client.post(
            "/api/calendar/plan",
            json={
                "date_range_start": "2026-03-27",
                "date_range_end": "2026-03-21",
                "platforms": ["facebook"],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 400

    @patch("api.routes.calendar_plan._run_claude")
    def test_constraints_passed(self, mock_claude, client, auth_headers, db_engine):
        mock_claude.return_value = MOCK_CLAUDE_RESPONSE
        _seed_pillars(db_engine)

        client.post(
            "/api/calendar/plan",
            json={
                "date_range_start": "2026-03-21",
                "date_range_end": "2026-03-27",
                "platforms": ["facebook"],
                "constraints": "Focus on farm content this week",
            },
            headers=auth_headers,
        )
        prompt = mock_claude.call_args[0][0]
        assert "Focus on farm content this week" in prompt
