"""Tests for OAuth token health monitoring.

Tests verify:
- check_oauth_health uses 'claude auth status' (JSON output)
- Authenticated returns (True, message with auth method)
- Not logged in returns (False, message with login hint)
- Timeout returns (False, timeout message)
- CLI not found returns (False, message)
"""

import json
from unittest.mock import MagicMock, patch


class TestCheckOauthHealth:
    """Test OAuth token health checking via 'claude auth status'."""

    @patch("content_engine.health.subprocess.run")
    def test_valid_token_returns_true(self, mock_run: MagicMock) -> None:
        from content_engine.health import check_oauth_health

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"loggedIn": True, "authMethod": "claude.ai"}),
        )
        ok, msg = check_oauth_health()
        assert ok is True
        assert "claude.ai" in msg

    @patch("content_engine.health.subprocess.run")
    def test_api_key_auth_returns_true(self, mock_run: MagicMock) -> None:
        from content_engine.health import check_oauth_health

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"loggedIn": True, "authMethod": "api_key"}),
        )
        ok, msg = check_oauth_health()
        assert ok is True
        assert "api_key" in msg

    @patch("content_engine.health.subprocess.run")
    def test_not_logged_in_returns_false(self, mock_run: MagicMock) -> None:
        from content_engine.health import check_oauth_health

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"loggedIn": False}),
        )
        ok, msg = check_oauth_health()
        assert ok is False
        assert "login" in msg.lower()

    @patch("content_engine.health.subprocess.run")
    def test_timeout_returns_false(self, mock_run: MagicMock) -> None:
        import subprocess

        from content_engine.health import check_oauth_health

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=10)
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
    def test_invalid_json_returns_false(self, mock_run: MagicMock) -> None:
        from content_engine.health import check_oauth_health

        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="not json",
        )
        ok, msg = check_oauth_health()
        assert ok is False
        assert msg
