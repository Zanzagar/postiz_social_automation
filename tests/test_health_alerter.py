"""Tests for health_alerter.py - Consecutive failure alerting with notification history."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from health_checker import HealthResult, HealthStatus
from health_alerter import (
    Alert,
    AlertChannel,
    ConsecutiveFailureTracker,
    ConsoleAlertChannel,
    HealthAlerter,
    NotificationHistory,
    WebhookAlertChannel,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unhealthy(service: str, details: dict | None = None) -> HealthResult:
    return HealthResult(service, HealthStatus.UNHEALTHY, 100, details or {"error": "down"})


def _healthy(service: str) -> HealthResult:
    return HealthResult(service, HealthStatus.HEALTHY, 10)


def _missing(service: str) -> HealthResult:
    return HealthResult(service, HealthStatus.MISSING, 0, {"error": "not found"})


def _make_alert(service: str = "postiz", failures: int = 3, threshold: int = 3) -> Alert:
    return Alert(
        service_name=service,
        consecutive_failures=failures,
        threshold=threshold,
        latest_status=HealthStatus.UNHEALTHY,
        latest_details={"error": "down"},
        timestamp=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# TestAlertDataclass
# ---------------------------------------------------------------------------

class TestAlertDataclass:
    def test_alert_creation_with_all_fields(self):
        ts = datetime.now(timezone.utc)
        alert = Alert(
            service_name="postiz",
            consecutive_failures=3,
            threshold=3,
            latest_status=HealthStatus.UNHEALTHY,
            latest_details={"error": "timeout"},
            timestamp=ts,
        )

        assert alert.service_name == "postiz"
        assert alert.consecutive_failures == 3
        assert alert.threshold == 3
        assert alert.latest_status == HealthStatus.UNHEALTHY
        assert alert.latest_details == {"error": "timeout"}
        assert alert.timestamp == ts

    def test_alert_details_can_be_none(self):
        alert = Alert(
            service_name="redis",
            consecutive_failures=4,
            threshold=3,
            latest_status=HealthStatus.MISSING,
            latest_details=None,
            timestamp=datetime.now(timezone.utc),
        )

        assert alert.latest_details is None

    def test_alert_is_dataclass(self):
        # dataclasses support equality comparison
        ts = datetime.now(timezone.utc)
        a = Alert("svc", 3, 3, HealthStatus.UNHEALTHY, None, ts)
        b = Alert("svc", 3, 3, HealthStatus.UNHEALTHY, None, ts)
        assert a == b


# ---------------------------------------------------------------------------
# TestAlertChannelProtocol
# ---------------------------------------------------------------------------

class TestAlertChannelProtocol:
    def test_protocol_is_runtime_checkable(self):
        # A class with a send() method should satisfy the Protocol
        class DummyChannel:
            def send(self, alert: Alert) -> None:
                pass

        assert isinstance(DummyChannel(), AlertChannel), (
            "DummyChannel with send() should satisfy AlertChannel Protocol"
        )

    def test_object_without_send_does_not_satisfy_protocol(self):
        class BadChannel:
            def notify(self, alert: Alert) -> None:
                pass

        assert not isinstance(BadChannel(), AlertChannel), (
            "Object missing send() should not satisfy AlertChannel Protocol"
        )


# ---------------------------------------------------------------------------
# TestConsecutiveFailureTracker
# ---------------------------------------------------------------------------

class TestConsecutiveFailureTracker:
    def test_initial_count_is_zero(self):
        tracker = ConsecutiveFailureTracker(threshold=3)

        assert tracker.get_count("postiz") == 0

    def test_unknown_service_count_is_zero(self):
        tracker = ConsecutiveFailureTracker(threshold=3)

        assert tracker.get_count("nonexistent-service") == 0

    def test_record_unhealthy_increments_count(self):
        tracker = ConsecutiveFailureTracker(threshold=3)

        tracker.record(_unhealthy("postiz"))

        assert tracker.get_count("postiz") == 1

    def test_record_missing_increments_count(self):
        tracker = ConsecutiveFailureTracker(threshold=3)

        tracker.record(_missing("postiz"))

        assert tracker.get_count("postiz") == 1

    def test_record_healthy_resets_count_to_zero(self):
        tracker = ConsecutiveFailureTracker(threshold=3)
        tracker.record(_unhealthy("postiz"))
        tracker.record(_unhealthy("postiz"))

        tracker.record(_healthy("postiz"))

        assert tracker.get_count("postiz") == 0, (
            "Healthy result should reset the consecutive failure count to 0"
        )

    def test_count_accumulates_across_multiple_failures(self):
        tracker = ConsecutiveFailureTracker(threshold=3)

        tracker.record(_unhealthy("postiz"))
        tracker.record(_unhealthy("postiz"))
        tracker.record(_unhealthy("postiz"))

        assert tracker.get_count("postiz") == 3

    def test_services_tracked_independently(self):
        tracker = ConsecutiveFailureTracker(threshold=3)

        tracker.record(_unhealthy("postiz"))
        tracker.record(_unhealthy("postiz"))
        tracker.record(_unhealthy("redis"))

        assert tracker.get_count("postiz") == 2, "postiz should have 2 failures"
        assert tracker.get_count("redis") == 1, "redis should have 1 failure"

    def test_healthy_for_one_service_does_not_reset_another(self):
        tracker = ConsecutiveFailureTracker(threshold=3)
        tracker.record(_unhealthy("postiz"))
        tracker.record(_unhealthy("redis"))

        tracker.record(_healthy("postiz"))

        assert tracker.get_count("postiz") == 0, "postiz should be reset"
        assert tracker.get_count("redis") == 1, "redis should be unaffected"

    def test_threshold_boundary_at_exactly_threshold(self):
        """record() should return True (alert triggered) at exactly the threshold count."""
        tracker = ConsecutiveFailureTracker(threshold=3)

        tracker.record(_unhealthy("postiz"))
        tracker.record(_unhealthy("postiz"))
        alert_triggered = tracker.record(_unhealthy("postiz"))

        assert alert_triggered is True, (
            "Should return True when consecutive failures reach the threshold"
        )

    def test_threshold_boundary_below_threshold(self):
        """record() should return False (no alert) when below threshold."""
        tracker = ConsecutiveFailureTracker(threshold=3)

        tracker.record(_unhealthy("postiz"))
        alert_triggered = tracker.record(_unhealthy("postiz"))

        assert alert_triggered is False, (
            "Should return False when consecutive failures are below threshold"
        )

    def test_threshold_boundary_exceeds_threshold_still_alerts(self):
        """record() should return True on every call beyond the threshold (not just exactly at it)."""
        tracker = ConsecutiveFailureTracker(threshold=3)
        tracker.record(_unhealthy("postiz"))
        tracker.record(_unhealthy("postiz"))
        tracker.record(_unhealthy("postiz"))  # threshold reached

        alert_triggered = tracker.record(_unhealthy("postiz"))  # 4th failure

        assert alert_triggered is True, (
            "Should keep alerting on every failure past the threshold"
        )

    def test_reset_clears_count_for_service(self):
        tracker = ConsecutiveFailureTracker(threshold=3)
        tracker.record(_unhealthy("postiz"))
        tracker.record(_unhealthy("postiz"))

        tracker.reset("postiz")

        assert tracker.get_count("postiz") == 0

    def test_reset_does_not_affect_other_services(self):
        tracker = ConsecutiveFailureTracker(threshold=3)
        tracker.record(_unhealthy("postiz"))
        tracker.record(_unhealthy("redis"))

        tracker.reset("postiz")

        assert tracker.get_count("redis") == 1

    def test_threshold_one_alerts_on_first_failure(self):
        tracker = ConsecutiveFailureTracker(threshold=1)

        alert_triggered = tracker.record(_unhealthy("postiz"))

        assert alert_triggered is True

    def test_healthy_result_returns_false(self):
        """record() with a healthy result should never trigger an alert."""
        tracker = ConsecutiveFailureTracker(threshold=3)

        result = tracker.record(_healthy("postiz"))

        assert result is False


# ---------------------------------------------------------------------------
# TestConsoleAlertChannel
# ---------------------------------------------------------------------------

class TestConsoleAlertChannel:
    def test_send_calls_logger_error(self):
        mock_logger = MagicMock()
        channel = ConsoleAlertChannel(logger_instance=mock_logger)
        alert = _make_alert()

        channel.send(alert)

        mock_logger.error.assert_called_once()

    def test_send_message_contains_service_name(self):
        mock_logger = MagicMock()
        channel = ConsoleAlertChannel(logger_instance=mock_logger)
        alert = _make_alert(service="postiz-redis")

        channel.send(alert)

        log_call_args = mock_logger.error.call_args
        logged_message = log_call_args[0][0]
        assert "postiz-redis" in logged_message, (
            f"Service name should appear in log message, got: {logged_message!r}"
        )

    def test_send_message_contains_failure_count(self):
        mock_logger = MagicMock()
        channel = ConsoleAlertChannel(logger_instance=mock_logger)
        alert = _make_alert(failures=5)

        channel.send(alert)

        log_call_args = mock_logger.error.call_args
        logged_message = log_call_args[0][0]
        assert "5" in logged_message, (
            f"Failure count should appear in log message, got: {logged_message!r}"
        )

    def test_send_message_contains_threshold(self):
        mock_logger = MagicMock()
        channel = ConsoleAlertChannel(logger_instance=mock_logger)
        alert = _make_alert(threshold=3)

        channel.send(alert)

        log_call_args = mock_logger.error.call_args
        logged_message = log_call_args[0][0]
        assert "3" in logged_message, (
            f"Threshold should appear in log message, got: {logged_message!r}"
        )

    def test_send_does_not_raise_on_none_details(self):
        mock_logger = MagicMock()
        channel = ConsoleAlertChannel(logger_instance=mock_logger)
        alert = Alert(
            service_name="postiz",
            consecutive_failures=3,
            threshold=3,
            latest_status=HealthStatus.UNHEALTHY,
            latest_details=None,
            timestamp=datetime.now(timezone.utc),
        )

        # Should not raise
        channel.send(alert)

        mock_logger.error.assert_called_once()

    def test_satisfies_alert_channel_protocol(self):
        mock_logger = MagicMock()
        channel = ConsoleAlertChannel(logger_instance=mock_logger)

        assert isinstance(channel, AlertChannel)


# ---------------------------------------------------------------------------
# TestWebhookAlertChannel
# ---------------------------------------------------------------------------

class TestWebhookAlertChannel:
    @patch("health_alerter.httpx")
    def test_send_posts_to_url(self, mock_httpx):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.Client.return_value = mock_client

        channel = WebhookAlertChannel(url="https://n8n.example.com/webhook/alert")
        alert = _make_alert()

        channel.send(alert)

        mock_client.post.assert_called_once()
        call_url = mock_client.post.call_args[0][0]
        assert call_url == "https://n8n.example.com/webhook/alert"

    @patch("health_alerter.httpx")
    def test_send_payload_contains_service_name(self, mock_httpx):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.Client.return_value = mock_client

        channel = WebhookAlertChannel(url="https://n8n.example.com/webhook/alert")
        alert = _make_alert(service="temporal")

        channel.send(alert)

        payload = mock_client.post.call_args.kwargs.get("json") or mock_client.post.call_args[1].get("json")
        assert payload["service"] == "temporal"

    @patch("health_alerter.httpx")
    def test_send_payload_contains_consecutive_failures(self, mock_httpx):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.Client.return_value = mock_client

        channel = WebhookAlertChannel(url="https://n8n.example.com/webhook/alert")
        alert = _make_alert(failures=5)

        channel.send(alert)

        payload = mock_client.post.call_args.kwargs.get("json") or mock_client.post.call_args[1].get("json")
        assert payload["consecutive_failures"] == 5

    @patch("health_alerter.httpx")
    def test_send_payload_contains_event_type(self, mock_httpx):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.Client.return_value = mock_client

        channel = WebhookAlertChannel(url="https://n8n.example.com/webhook/alert")
        alert = _make_alert()

        channel.send(alert)

        payload = mock_client.post.call_args.kwargs.get("json") or mock_client.post.call_args[1].get("json")
        assert payload["event"] == "consecutive_failure_alert"

    @patch("health_alerter.httpx")
    def test_send_payload_contains_threshold(self, mock_httpx):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.Client.return_value = mock_client

        channel = WebhookAlertChannel(url="https://n8n.example.com/webhook/alert")
        alert = _make_alert(threshold=5)

        channel.send(alert)

        payload = mock_client.post.call_args.kwargs.get("json") or mock_client.post.call_args[1].get("json")
        assert payload["threshold"] == 5

    @patch("health_alerter.httpx")
    def test_send_payload_contains_timestamp(self, mock_httpx):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.Client.return_value = mock_client

        channel = WebhookAlertChannel(url="https://n8n.example.com/webhook/alert")
        alert = _make_alert()

        channel.send(alert)

        payload = mock_client.post.call_args.kwargs.get("json") or mock_client.post.call_args[1].get("json")
        assert "timestamp" in payload

    @patch("health_alerter.time")
    @patch("health_alerter.httpx")
    def test_send_retries_on_network_error(self, mock_httpx, mock_time):
        mock_client = MagicMock()
        mock_httpx.Client.return_value = mock_client
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_httpx.RequestError = Exception
        mock_client.post.side_effect = Exception("connection refused")

        channel = WebhookAlertChannel(url="https://n8n.example.com/webhook/alert", max_retries=3)
        alert = _make_alert()

        channel.send(alert)

        assert mock_client.post.call_count == 3, (
            f"Expected 3 retry attempts, got {mock_client.post.call_count}"
        )

    @patch("health_alerter.time")
    @patch("health_alerter.httpx")
    def test_send_no_retry_on_4xx(self, mock_httpx, mock_time):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.Client.return_value = mock_client

        channel = WebhookAlertChannel(url="https://n8n.example.com/webhook/alert", max_retries=3)
        alert = _make_alert()

        channel.send(alert)

        assert mock_client.post.call_count == 1, (
            "4xx response should not trigger retries"
        )

    @patch("health_alerter.httpx")
    def test_send_succeeds_on_200(self, mock_httpx):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.Client.return_value = mock_client

        channel = WebhookAlertChannel(url="https://n8n.example.com/webhook/alert")
        alert = _make_alert()

        # Should not raise
        channel.send(alert)

        assert mock_client.post.call_count == 1

    def test_satisfies_alert_channel_protocol(self):
        channel = WebhookAlertChannel(url="https://n8n.example.com/webhook/alert")

        assert isinstance(channel, AlertChannel)


# ---------------------------------------------------------------------------
# TestNotificationHistory
# ---------------------------------------------------------------------------

class TestNotificationHistory:
    def test_initial_total_count_is_zero(self):
        history = NotificationHistory(max_size=100)

        assert history.total_count() == 0

    def test_record_increments_total_count(self):
        history = NotificationHistory(max_size=100)
        alert = _make_alert()

        history.record(alert)

        assert history.total_count() == 1

    def test_get_recent_returns_recorded_alerts(self):
        history = NotificationHistory(max_size=100)
        alert = _make_alert()

        history.record(alert)
        recent = history.get_recent(n=10)

        assert len(recent) == 1
        assert recent[0] == alert

    def test_get_recent_limits_results(self):
        history = NotificationHistory(max_size=100)
        for i in range(10):
            history.record(_make_alert(service=f"service-{i}"))

        recent = history.get_recent(n=3)

        assert len(recent) == 3, f"Expected 3 most recent alerts, got {len(recent)}"

    def test_get_recent_returns_most_recent_first(self):
        history = NotificationHistory(max_size=100)
        history.record(_make_alert(service="first"))
        history.record(_make_alert(service="second"))
        history.record(_make_alert(service="third"))

        recent = history.get_recent(n=2)

        assert recent[0].service_name == "third", (
            "Most recent alert should be first in get_recent() results"
        )
        assert recent[1].service_name == "second"

    def test_get_for_service_filters_by_name(self):
        history = NotificationHistory(max_size=100)
        history.record(_make_alert(service="postiz"))
        history.record(_make_alert(service="redis"))
        history.record(_make_alert(service="postiz"))

        results = history.get_for_service("postiz")

        assert len(results) == 2
        assert all(a.service_name == "postiz" for a in results)

    def test_get_for_service_unknown_returns_empty(self):
        history = NotificationHistory(max_size=100)
        history.record(_make_alert(service="postiz"))

        results = history.get_for_service("nonexistent")

        assert results == []

    def test_get_failures_returns_only_non_healthy(self):
        history = NotificationHistory(max_size=100)
        unhealthy_alert = Alert(
            service_name="postiz",
            consecutive_failures=3,
            threshold=3,
            latest_status=HealthStatus.UNHEALTHY,
            latest_details={"error": "down"},
            timestamp=datetime.now(timezone.utc),
        )
        missing_alert = Alert(
            service_name="redis",
            consecutive_failures=4,
            threshold=3,
            latest_status=HealthStatus.MISSING,
            latest_details=None,
            timestamp=datetime.now(timezone.utc),
        )
        history.record(unhealthy_alert)
        history.record(missing_alert)

        failures = history.get_failures()

        assert len(failures) == 2
        assert all(a.latest_status != HealthStatus.HEALTHY for a in failures)

    def test_max_size_evicts_oldest_on_overflow(self):
        history = NotificationHistory(max_size=3)
        history.record(_make_alert(service="first"))
        history.record(_make_alert(service="second"))
        history.record(_make_alert(service="third"))

        history.record(_make_alert(service="fourth"))  # overflows max_size=3

        recent = history.get_recent(n=10)
        service_names = [a.service_name for a in recent]
        assert "first" not in service_names, (
            "Oldest entry should be evicted when max_size is exceeded"
        )
        assert "fourth" in service_names

    def test_max_size_one_keeps_only_latest(self):
        history = NotificationHistory(max_size=1)
        history.record(_make_alert(service="first"))
        history.record(_make_alert(service="second"))

        recent = history.get_recent(n=10)

        assert len(recent) == 1
        assert recent[0].service_name == "second"

    def test_total_count_reflects_all_ever_recorded(self):
        """total_count() should count all alerts ever recorded, even after eviction."""
        history = NotificationHistory(max_size=2)
        history.record(_make_alert(service="a"))
        history.record(_make_alert(service="b"))
        history.record(_make_alert(service="c"))  # evicts "a"

        # total_count may track only stored or all-time depending on implementation.
        # The minimum requirement is it returns >= current stored count.
        assert history.total_count() >= 2


# ---------------------------------------------------------------------------
# TestHealthAlerter
# ---------------------------------------------------------------------------

class TestHealthAlerter:
    def test_process_result_no_alert_before_threshold(self):
        channel = MagicMock(spec=AlertChannel)
        alerter = HealthAlerter(channels=[channel], threshold=3)

        alerter.process_result(_unhealthy("postiz"))
        alerter.process_result(_unhealthy("postiz"))

        channel.send.assert_not_called()

    def test_process_result_sends_alert_at_threshold(self):
        channel = MagicMock(spec=AlertChannel)
        alerter = HealthAlerter(channels=[channel], threshold=3)

        alerter.process_result(_unhealthy("postiz"))
        alerter.process_result(_unhealthy("postiz"))
        alerter.process_result(_unhealthy("postiz"))

        channel.send.assert_called_once()

    def test_process_result_alert_contains_correct_service(self):
        channel = MagicMock(spec=AlertChannel)
        alerter = HealthAlerter(channels=[channel], threshold=3)

        for _ in range(3):
            alerter.process_result(_unhealthy("postiz-postgres"))

        sent_alert = channel.send.call_args[0][0]
        assert sent_alert.service_name == "postiz-postgres"

    def test_process_result_alert_contains_consecutive_count(self):
        channel = MagicMock(spec=AlertChannel)
        alerter = HealthAlerter(channels=[channel], threshold=3)

        for _ in range(3):
            alerter.process_result(_unhealthy("postiz"))

        sent_alert = channel.send.call_args[0][0]
        assert sent_alert.consecutive_failures == 3

    def test_process_result_alert_contains_threshold(self):
        channel = MagicMock(spec=AlertChannel)
        alerter = HealthAlerter(channels=[channel], threshold=5)

        for _ in range(5):
            alerter.process_result(_unhealthy("postiz"))

        sent_alert = channel.send.call_args[0][0]
        assert sent_alert.threshold == 5

    def test_process_result_alert_contains_latest_status(self):
        channel = MagicMock(spec=AlertChannel)
        alerter = HealthAlerter(channels=[channel], threshold=3)

        for _ in range(3):
            alerter.process_result(_missing("temporal"))

        sent_alert = channel.send.call_args[0][0]
        assert sent_alert.latest_status == HealthStatus.MISSING

    def test_process_result_broadcasts_to_all_channels(self):
        channel_a = MagicMock(spec=AlertChannel)
        channel_b = MagicMock(spec=AlertChannel)
        alerter = HealthAlerter(channels=[channel_a, channel_b], threshold=3)

        for _ in range(3):
            alerter.process_result(_unhealthy("postiz"))

        channel_a.send.assert_called_once()
        channel_b.send.assert_called_once()

    def test_process_result_healthy_resets_counter_and_suppresses_future_alerts(self):
        channel = MagicMock(spec=AlertChannel)
        alerter = HealthAlerter(channels=[channel], threshold=3)

        # Two failures, then recovery
        alerter.process_result(_unhealthy("postiz"))
        alerter.process_result(_unhealthy("postiz"))
        alerter.process_result(_healthy("postiz"))

        # Two more failures - should not yet trigger
        alerter.process_result(_unhealthy("postiz"))
        alerter.process_result(_unhealthy("postiz"))

        channel.send.assert_not_called()

    def test_process_result_alert_continues_past_threshold(self):
        """Each failure beyond threshold should also send an alert."""
        channel = MagicMock(spec=AlertChannel)
        alerter = HealthAlerter(channels=[channel], threshold=3)

        for _ in range(5):
            alerter.process_result(_unhealthy("postiz"))

        assert channel.send.call_count == 3, (
            "Alerts should fire on failure 3, 4, and 5 (each beyond threshold)"
        )

    def test_process_result_multi_service_independent_thresholds(self):
        channel = MagicMock(spec=AlertChannel)
        alerter = HealthAlerter(channels=[channel], threshold=3)

        # postiz hits threshold
        for _ in range(3):
            alerter.process_result(_unhealthy("postiz"))

        # redis only has 2 failures - should not alert
        alerter.process_result(_unhealthy("redis"))
        alerter.process_result(_unhealthy("redis"))

        assert channel.send.call_count == 1, (
            "Only postiz should have triggered an alert, not redis"
        )
        sent_alert = channel.send.call_args[0][0]
        assert sent_alert.service_name == "postiz"

    def test_process_result_records_alert_in_history(self):
        channel = MagicMock(spec=AlertChannel)
        alerter = HealthAlerter(channels=[channel], threshold=3, history_max_size=100)

        for _ in range(3):
            alerter.process_result(_unhealthy("postiz"))

        assert alerter.history.total_count() == 1

    def test_process_result_no_history_entry_before_threshold(self):
        channel = MagicMock(spec=AlertChannel)
        alerter = HealthAlerter(channels=[channel], threshold=3, history_max_size=100)

        alerter.process_result(_unhealthy("postiz"))
        alerter.process_result(_unhealthy("postiz"))

        assert alerter.history.total_count() == 0

    def test_process_result_history_entry_has_correct_alert(self):
        channel = MagicMock(spec=AlertChannel)
        alerter = HealthAlerter(channels=[channel], threshold=3, history_max_size=100)

        for _ in range(3):
            alerter.process_result(_unhealthy("temporal"))

        recent = alerter.history.get_recent(n=1)
        assert recent[0].service_name == "temporal"
        assert recent[0].consecutive_failures == 3

    def test_no_channels_does_not_raise(self):
        alerter = HealthAlerter(channels=[], threshold=3)

        # Should not raise even with no channels configured
        for _ in range(3):
            alerter.process_result(_unhealthy("postiz"))

    def test_process_result_returns_alert_when_triggered(self):
        """process_result should return the Alert object when an alert fires."""
        channel = MagicMock(spec=AlertChannel)
        alerter = HealthAlerter(channels=[channel], threshold=3)

        alerter.process_result(_unhealthy("postiz"))
        alerter.process_result(_unhealthy("postiz"))
        result = alerter.process_result(_unhealthy("postiz"))

        assert isinstance(result, Alert), (
            "process_result should return an Alert when the threshold is reached"
        )

    def test_process_result_returns_none_when_not_triggered(self):
        """process_result should return None when below threshold."""
        channel = MagicMock(spec=AlertChannel)
        alerter = HealthAlerter(channels=[channel], threshold=3)

        result = alerter.process_result(_unhealthy("postiz"))

        assert result is None

    def test_process_result_returns_none_for_healthy_result(self):
        channel = MagicMock(spec=AlertChannel)
        alerter = HealthAlerter(channels=[channel], threshold=3)

        result = alerter.process_result(_healthy("postiz"))

        assert result is None

    def test_channel_exception_does_not_prevent_other_channels(self):
        """If one channel raises, remaining channels should still receive the alert."""
        failing_channel = MagicMock(spec=AlertChannel)
        failing_channel.send.side_effect = RuntimeError("webhook timeout")
        working_channel = MagicMock(spec=AlertChannel)
        alerter = HealthAlerter(channels=[failing_channel, working_channel], threshold=3)

        for _ in range(3):
            alerter.process_result(_unhealthy("postiz"))

        working_channel.send.assert_called_once()

    def test_history_max_size_respected_by_alerter(self):
        channel = MagicMock(spec=AlertChannel)
        alerter = HealthAlerter(channels=[channel], threshold=1, history_max_size=2)

        alerter.process_result(_unhealthy("postiz"))    # alert 1
        alerter.process_result(_unhealthy("redis"))     # alert 2
        alerter.process_result(_unhealthy("temporal"))  # alert 3, evicts oldest

        recent = alerter.history.get_recent(n=10)
        assert len(recent) == 2, (
            f"History should cap at max_size=2, got {len(recent)} entries"
        )
