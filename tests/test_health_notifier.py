"""Tests for health_notifier.py - State transition detection and webhook notifications."""

from unittest.mock import MagicMock, patch

import pytest

from health_checker import HealthResult, HealthStatus
from health_notifier import HealthNotifier


class TestProcessResult:
    def test_first_check_records_but_no_transition(self, temp_db):
        notifier = HealthNotifier(temp_db, webhook_url="")
        result = HealthResult("postiz", HealthStatus.HEALTHY, 50, {"ok": True})

        transition_id = notifier.process_result(result)

        assert transition_id is None
        assert temp_db.get_last_status("postiz") == "healthy"

    def test_same_status_no_transition(self, temp_db):
        temp_db.record_check("postiz", "healthy", 50)
        notifier = HealthNotifier(temp_db, webhook_url="")
        result = HealthResult("postiz", HealthStatus.HEALTHY, 42)

        transition_id = notifier.process_result(result)

        assert transition_id is None

    def test_status_change_creates_transition(self, temp_db):
        temp_db.record_check("postiz", "healthy", 50)
        notifier = HealthNotifier(temp_db, webhook_url="")
        result = HealthResult("postiz", HealthStatus.UNHEALTHY, 100, {"error": "down"})

        transition_id = notifier.process_result(result)

        assert transition_id is not None
        assert isinstance(transition_id, int)

    def test_transition_recorded_in_storage(self, temp_db):
        import sqlite3

        temp_db.record_check("postiz", "healthy", 50)
        notifier = HealthNotifier(temp_db, webhook_url="")
        result = HealthResult("postiz", HealthStatus.UNHEALTHY, 100)

        tid = notifier.process_result(result)

        with sqlite3.connect(temp_db.db_path) as conn:
            row = conn.execute(
                "SELECT from_status, to_status FROM state_transitions WHERE id = ?",
                (tid,),
            ).fetchone()
        assert row[0] == "healthy"
        assert row[1] == "unhealthy"


class TestWebhookSending:
    @patch("health_notifier.httpx")
    def test_webhook_sent_on_transition(self, mock_httpx, temp_db):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.Client.return_value = mock_client

        temp_db.record_check("postiz", "healthy", 50)
        notifier = HealthNotifier(temp_db, webhook_url="https://n8n.example.com/webhook/test")
        result = HealthResult("postiz", HealthStatus.UNHEALTHY, 100, {"error": "down"})

        notifier.process_result(result)

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["event"] == "service_status_change"
        assert payload["service"] == "postiz"
        assert payload["from_status"] == "healthy"
        assert payload["to_status"] == "unhealthy"

    @patch("health_notifier.httpx")
    def test_no_webhook_without_url(self, mock_httpx, temp_db):
        temp_db.record_check("postiz", "healthy", 50)
        notifier = HealthNotifier(temp_db, webhook_url="")
        result = HealthResult("postiz", HealthStatus.UNHEALTHY, 100)

        notifier.process_result(result)

        mock_httpx.Client.assert_not_called()

    @patch("health_notifier.httpx")
    def test_webhook_marks_sent_on_success(self, mock_httpx, temp_db):
        import sqlite3

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.Client.return_value = mock_client

        temp_db.record_check("postiz", "healthy", 50)
        notifier = HealthNotifier(temp_db, webhook_url="https://n8n.example.com/webhook/test")
        result = HealthResult("postiz", HealthStatus.UNHEALTHY, 100)

        tid = notifier.process_result(result)

        with sqlite3.connect(temp_db.db_path) as conn:
            row = conn.execute(
                "SELECT webhook_sent FROM state_transitions WHERE id = ?", (tid,)
            ).fetchone()
        assert row[0] == 1

    @patch("health_notifier.time.sleep")
    @patch("health_notifier.httpx")
    def test_webhook_retries_on_failure(self, mock_httpx, mock_sleep, temp_db):
        mock_client = MagicMock()
        mock_httpx.Client.return_value = mock_client
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_httpx.RequestError = Exception
        mock_client.post.side_effect = Exception("connection error")

        notifier = HealthNotifier(temp_db, webhook_url="https://n8n.example.com/webhook/test")
        success = notifier.send_webhook("postiz", "healthy", "unhealthy", None)

        assert success is False
        assert mock_client.post.call_count == 3

    @patch("health_notifier.httpx")
    def test_webhook_no_retry_on_4xx(self, mock_httpx, temp_db):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.Client.return_value = mock_client

        notifier = HealthNotifier(temp_db, webhook_url="https://n8n.example.com/webhook/test")
        success = notifier.send_webhook("postiz", "healthy", "unhealthy", None)

        assert success is False
        assert mock_client.post.call_count == 1


class TestWebhookPayload:
    @patch("health_notifier.httpx")
    def test_payload_structure(self, mock_httpx, temp_db):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.Client.return_value = mock_client

        notifier = HealthNotifier(temp_db, webhook_url="https://n8n.example.com/webhook/test")
        notifier.send_webhook("postiz", "healthy", "unhealthy", {"error": "timeout"})

        payload = mock_client.post.call_args.kwargs.get("json") or mock_client.post.call_args[1].get("json")
        assert payload["event"] == "service_status_change"
        assert payload["service"] == "postiz"
        assert payload["from_status"] == "healthy"
        assert payload["to_status"] == "unhealthy"
        assert payload["details"] == "timeout"
        assert payload["stack"] == "postiz-social-automation"
        assert "timestamp" in payload
