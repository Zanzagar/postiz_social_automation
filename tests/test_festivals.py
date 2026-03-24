"""Tests for ISKCON festival calendar API and data file."""

import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.routes.festivals import CALENDAR_PATH, _load_festivals


class TestFestivalDataFile:
    def test_calendar_file_exists(self):
        assert CALENDAR_PATH.exists(), f"Missing: {CALENDAR_PATH}"

    def test_calendar_is_valid_json(self):
        data = json.loads(CALENDAR_PATH.read_text())
        assert isinstance(data, list)
        assert len(data) > 0

    def test_all_festivals_have_required_fields(self):
        data = json.loads(CALENDAR_PATH.read_text())
        required = {
            "name",
            "date",
            "significance",
            "suggested_content_angles",
            "topic",
            "content_pillar",
        }
        for fest in data:
            missing = required - set(fest.keys())
            assert not missing, f"Festival '{fest.get('name', '?')}' missing: {missing}"

    def test_dates_are_valid_format(self):
        data = json.loads(CALENDAR_PATH.read_text())
        for fest in data:
            try:
                date.fromisoformat(fest["date"])
            except ValueError:
                pytest.fail(f"Invalid date format for '{fest['name']}': {fest['date']}")

    def test_topics_match_phase2_taxonomy(self):
        valid_topics = {
            "Cow Protection",
            "Ahimsa Dairy",
            "Farm Products",
            "Sustainability",
            "Retreats & Visits",
            "People & Team",
            "Education & Programs",
            "History & Mission",
            "Fundraising",
            "Spiritual Life",
            "Events & Festivals",
            "General Information",
        }
        data = json.loads(CALENDAR_PATH.read_text())
        for fest in data:
            assert fest["topic"] in valid_topics, (
                f"Festival '{fest['name']}' has invalid topic: '{fest['topic']}'"
            )

    def test_suggested_content_angles_are_lists(self):
        data = json.loads(CALENDAR_PATH.read_text())
        for fest in data:
            assert isinstance(fest["suggested_content_angles"], list)
            assert len(fest["suggested_content_angles"]) > 0

    def test_key_festivals_present(self):
        data = json.loads(CALENDAR_PATH.read_text())
        names = {f["name"] for f in data}
        key_festivals = {"Janmashtami", "Ratha Yatra", "Gaura Purnima", "Govardhan Puja"}
        missing = key_festivals - names
        assert not missing, f"Missing key festivals: {missing}"


class TestLoadFestivals:
    def test_loads_from_file(self):
        result = _load_festivals()
        assert len(result) > 0
        assert result[0]["name"]

    def test_returns_empty_for_missing_file(self):
        with patch("api.routes.festivals.CALENDAR_PATH", Path("/nonexistent/file.json")):
            result = _load_festivals()
            assert result == []


class TestFestivalsEndpoint:
    @pytest.fixture(autouse=True)
    def _env(self, monkeypatch):
        from api.dependencies import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("JWT_SECRET", "test-secret-key-min-32-chars-long!!")
        monkeypatch.setenv("API_PASSWORD", "testpass")
        monkeypatch.setenv("DATABASE_PATH", ":memory:")
        yield
        get_settings.cache_clear()

    @pytest.fixture
    def client(self):
        from api.main import app

        return TestClient(app)

    @pytest.fixture
    def auth_headers(self, client):
        resp = client.post("/api/auth/login", json={"password": "testpass"})
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_list_all_festivals(self, client, auth_headers):
        resp = client.get("/api/festivals", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        assert "name" in data[0]
        assert "significance" in data[0]

    def test_filter_by_date_range(self, client, auth_headers):
        resp = client.get(
            "/api/festivals",
            params={"from": "2026-08-01", "to": "2026-09-30"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        for fest in data:
            fest_date = date.fromisoformat(fest["date"])
            assert date(2026, 8, 1) <= fest_date <= date(2026, 9, 30)

    def test_filter_returns_empty_for_no_match(self, client, auth_headers):
        resp = client.get(
            "/api/festivals",
            params={"from": "2025-01-01", "to": "2025-01-31"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_requires_auth(self, client):
        resp = client.get("/api/festivals")
        assert resp.status_code == 401
