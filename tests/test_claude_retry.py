"""Tests for _call_claude() retry logic with exponential backoff — Task 19.

Covers:
- Succeeds on first try (no retry)
- Succeeds on retry after first failure
- Gives up after max retries (3 total attempts)
- Timeout errors are NOT retried
"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from content_engine.generator import _call_claude


class TestCallClaudeNoRetry:
    """When the first call succeeds, no retry should happen."""

    @patch("content_engine.generator.subprocess.run")
    def test_success_first_try(self, mock_run) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Hello world",
            stderr="",
        )
        result = _call_claude("test prompt")
        assert result == "Hello world"
        assert mock_run.call_count == 1


class TestCallClaudeRetrySuccess:
    """When the first call fails but a retry succeeds."""

    @patch("content_engine.generator.time.sleep")
    @patch("content_engine.generator.subprocess.run")
    def test_succeeds_on_second_try(self, mock_run, mock_sleep) -> None:
        fail = MagicMock(returncode=1, stdout="", stderr="CLI error")
        success = MagicMock(returncode=0, stdout="recovered", stderr="")
        mock_run.side_effect = [fail, success]

        result = _call_claude("test prompt")
        assert result == "recovered"
        assert mock_run.call_count == 2
        # Should have slept 2s before first retry
        mock_sleep.assert_called_once_with(2)

    @patch("content_engine.generator.time.sleep")
    @patch("content_engine.generator.subprocess.run")
    def test_succeeds_on_third_try(self, mock_run, mock_sleep) -> None:
        fail = MagicMock(returncode=1, stdout="", stderr="CLI error")
        success = MagicMock(returncode=0, stdout="third time", stderr="")
        mock_run.side_effect = [fail, fail, success]

        result = _call_claude("test prompt")
        assert result == "third time"
        assert mock_run.call_count == 3
        # Should have slept 2s then 4s
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(2)
        mock_sleep.assert_any_call(4)


class TestCallClaudeRetryExhausted:
    """When all retries are exhausted, raise RuntimeError."""

    @patch("content_engine.generator.time.sleep")
    @patch("content_engine.generator.subprocess.run")
    def test_gives_up_after_max_retries(self, mock_run, mock_sleep) -> None:
        fail = MagicMock(returncode=1, stdout="", stderr="persistent failure")
        mock_run.return_value = fail

        with pytest.raises(RuntimeError, match="persistent failure"):
            _call_claude("test prompt")

        # 3 total attempts: initial + 2 retries
        assert mock_run.call_count == 3
        assert mock_sleep.call_count == 2


class TestCallClaudeTimeoutNoRetry:
    """Timeout errors should NOT be retried."""

    @patch("content_engine.generator.time.sleep")
    @patch("content_engine.generator.subprocess.run")
    def test_timeout_not_retried(self, mock_run, mock_sleep) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=120)

        with pytest.raises(RuntimeError, match="timed out"):
            _call_claude("test prompt")

        # Only 1 attempt — no retries for timeout
        assert mock_run.call_count == 1
        mock_sleep.assert_not_called()
