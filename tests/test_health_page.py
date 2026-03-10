"""Tests for the System Health page module."""

from pathlib import Path

from content_engine.health import check_claude_health, check_postiz_health, check_sheets_health


class TestCheckSheetsHealth:
    def test_returns_ok_when_service_reachable(self) -> None:
        """Returns (True, 'OK') when Sheets API responds."""
        result = check_sheets_health(sheets_client=None, skip_if_none=True)
        assert result == (True, "Not configured")

    def test_returns_error_on_exception(self) -> None:
        class FailingClient:
            def get_recent_errors(self, limit=1):
                raise ConnectionError("Network down")

        ok, msg = check_sheets_health(sheets_client=FailingClient())
        assert ok is False
        assert "Network down" in msg


class TestCheckPostizHealth:
    def test_returns_ok_when_api_responds(self) -> None:
        class MockPostiz:
            def list_integrations(self):
                return [{"id": "int_1"}]

        ok, msg = check_postiz_health(postiz_client=MockPostiz())
        assert ok is True
        assert "1 integration" in msg

    def test_returns_error_on_exception(self) -> None:
        class FailingPostiz:
            def list_integrations(self):
                raise ConnectionError("Connection refused")

        ok, msg = check_postiz_health(postiz_client=FailingPostiz())
        assert ok is False
        assert "Connection refused" in msg

    def test_returns_not_configured_when_none(self) -> None:
        ok, msg = check_postiz_health(postiz_client=None)
        assert ok is True
        assert msg == "Not configured"


class TestCheckClaudeHealth:
    def test_returns_ok_when_claude_available(self, monkeypatch) -> None:
        """Returns (True, version_string) when claude --version succeeds."""
        import subprocess

        def mock_run(*args, **kwargs):
            result = subprocess.CompletedProcess(args=args, returncode=0, stdout="claude 1.0.0\n")
            return result

        monkeypatch.setattr("content_engine.health.subprocess.run", mock_run)

        ok, msg = check_claude_health()
        assert ok is True
        assert "1.0.0" in msg

    def test_returns_error_when_claude_missing(self, monkeypatch) -> None:
        def mock_run(*args, **kwargs):
            raise FileNotFoundError("claude not found")

        monkeypatch.setattr("content_engine.health.subprocess.run", mock_run)

        ok, msg = check_claude_health()
        assert ok is False
        assert "not installed" in msg


class TestHealthPageExists:
    def test_health_page_file_exists(self) -> None:
        page = Path("app/pages/4_Health.py")
        assert page.exists(), f"Health page not found at {page}"
