"""Health endpoint: Sheets de-scoped honestly when no spreadsheet is configured.

When settings.spreadsheet_id is missing/empty/"placeholder", /api/health
reports sheets as ok ("Not configured (SQLite is the source of truth)")
WITHOUT calling the Sheets API. A real ID keeps the existing behavior.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from api.auth import get_current_user
from api.dependencies import get_postiz_client, get_sheets_client
from api.main import app

NOT_CONFIGURED_MSG = "Not configured (SQLite is the source of truth)"


def _settings(spreadsheet_id: str):
    return SimpleNamespace(demo_mode=False, spreadsheet_id=spreadsheet_id)


def _patched_checks(sheets_return=(True, "OK")):
    """Patch all health check functions so no real subprocess/API runs."""
    return (
        patch("api.routes.health.check_sheets_health", return_value=sheets_return),
        patch(
            "api.routes.health.check_postiz_health",
            return_value=(True, "2 integrations connected"),
        ),
        patch("api.routes.health.check_claude_health", return_value=(True, "claude 2.0.0")),
        patch("api.routes.health.check_oauth_health", return_value=(True, "Authenticated")),
    )


@pytest.fixture
def sheets_mock():
    mock = MagicMock()
    mock.get_recent_errors.return_value = []
    return mock


@pytest.fixture
def client(sheets_mock):
    from api.routes.health import _health_cache, _oauth_cache

    def _reset_caches():
        _health_cache["data"] = None
        _health_cache["expires"] = 0
        _oauth_cache["result"] = None
        _oauth_cache["expires"] = 0

    _reset_caches()
    app.dependency_overrides[get_current_user] = lambda: {"sub": "testuser"}
    app.dependency_overrides[get_sheets_client] = lambda: sheets_mock
    app.dependency_overrides[get_postiz_client] = lambda: MagicMock()
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    app.dependency_overrides.clear()
    _reset_caches()


@pytest.mark.asyncio
class TestSheetsDescope:
    async def test_placeholder_id_reports_ok_without_calling_sheets(self, client, sheets_mock):
        checks = _patched_checks()
        with (
            patch("api.routes.health.get_settings", return_value=_settings("placeholder")),
            checks[0] as sheets_check,
            checks[1],
            checks[2],
            checks[3],
        ):
            async with client as c:
                resp = await c.get("/api/health")

        assert resp.status_code == 200
        services = {s["name"]: s for s in resp.json()["services"]}
        assert set(services) == {"sheets", "postiz", "claude", "oauth"}
        assert services["sheets"]["status"] == "ok"
        assert services["sheets"]["message"] == NOT_CONFIGURED_MSG
        sheets_check.assert_not_called()
        sheets_mock.get_recent_errors.assert_not_called()

    async def test_empty_id_reports_ok_without_calling_sheets(self, client, sheets_mock):
        checks = _patched_checks()
        with (
            patch("api.routes.health.get_settings", return_value=_settings("")),
            checks[0] as sheets_check,
            checks[1],
            checks[2],
            checks[3],
        ):
            async with client as c:
                resp = await c.get("/api/health")

        services = {s["name"]: s for s in resp.json()["services"]}
        assert services["sheets"]["status"] == "ok"
        assert services["sheets"]["message"] == NOT_CONFIGURED_MSG
        sheets_check.assert_not_called()
        sheets_mock.get_recent_errors.assert_not_called()

    async def test_real_id_keeps_existing_check(self, client, sheets_mock):
        checks = _patched_checks(sheets_return=(True, "OK"))
        with (
            patch("api.routes.health.get_settings", return_value=_settings("1AbCRealSheetId")),
            checks[0] as sheets_check,
            checks[1],
            checks[2],
            checks[3],
        ):
            async with client as c:
                resp = await c.get("/api/health")

        services = {s["name"]: s for s in resp.json()["services"]}
        assert services["sheets"]["status"] == "ok"
        assert services["sheets"]["message"] == "OK"
        sheets_check.assert_called_once_with(sheets_mock)
        sheets_mock.get_recent_errors.assert_called_once_with(limit=10)

    async def test_real_id_error_still_reported(self, client, sheets_mock):
        checks = _patched_checks(sheets_return=(False, "HttpError 403: forbidden"))
        with (
            patch("api.routes.health.get_settings", return_value=_settings("1AbCRealSheetId")),
            checks[0],
            checks[1],
            checks[2],
            checks[3],
        ):
            async with client as c:
                resp = await c.get("/api/health")

        services = {s["name"]: s for s in resp.json()["services"]}
        assert services["sheets"]["status"] == "error"
        assert "403" in services["sheets"]["message"]
