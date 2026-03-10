"""Tests for OAuth token health monitoring (Task 24).

Tests verify:
- check_oauth_health function exists and returns (bool, str) tuple
- Healthy token returns (True, message)
- Expired/invalid token returns (False, message with re-auth hint)
- Timeout returns (False, timeout message)
- CLI not found returns (False, message)
"""

from unittest.mock import MagicMock, patch


class TestCheckOauthHealth:
    """Test OAuth token health checking."""

    @patch("content_engine.health.subprocess.run")
    def test_valid_token_returns_true(self, mock_run: MagicMock) -> None:
        from content_engine.health import check_oauth_health

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="OK",
            stderr="",
        )
        ok, msg = check_oauth_health()
        assert ok is True
        assert "valid" in msg.lower() or "ok" in msg.lower()

    @patch("content_engine.health.subprocess.run")
    def test_expired_token_returns_false(self, mock_run: MagicMock) -> None:
        from content_engine.health import check_oauth_health

        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: not authenticated. Please run 'claude login'",
        )
        ok, msg = check_oauth_health()
        assert ok is False
        assert "login" in msg.lower() or "expired" in msg.lower()

    @patch("content_engine.health.subprocess.run")
    def test_timeout_returns_false(self, mock_run: MagicMock) -> None:
        import subprocess

        from content_engine.health import check_oauth_health

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=30)
        ok, msg = check_oauth_health()
        assert ok is False
        assert "timeout" in msg.lower()

    @patch("content_engine.health.subprocess.run")
    def test_cli_not_found_returns_false(self, mock_run: MagicMock) -> None:
        from content_engine.health import check_oauth_health

        mock_run.side_effect = FileNotFoundError("claude not found")
        ok, msg = check_oauth_health()
        assert ok is False

    @patch("content_engine.health.subprocess.run")
    def test_unknown_error_returns_false(self, mock_run: MagicMock) -> None:
        from content_engine.health import check_oauth_health

        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Some unknown error",
        )
        ok, msg = check_oauth_health()
        assert ok is False
        assert msg  # Should have some message
