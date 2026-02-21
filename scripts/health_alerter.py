"""Consecutive failure alerting with notification history for health monitoring."""

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Protocol, runtime_checkable

import httpx

from health_checker import HealthResult, HealthStatus

logger = logging.getLogger("health_alerter")


@dataclass
class Alert:
    service_name: str
    consecutive_failures: int
    threshold: int
    latest_status: HealthStatus
    latest_details: Optional[dict] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@runtime_checkable
class AlertChannel(Protocol):
    def send(self, alert: Alert) -> None: ...


class ConsecutiveFailureTracker:
    def __init__(self, threshold: int = 3):
        self.threshold = threshold
        self._counts: dict[str, int] = {}

    def record(self, result: HealthResult) -> bool:
        service = result.service_name
        if result.status == HealthStatus.HEALTHY:
            self._counts[service] = 0
            return False

        self._counts[service] = self._counts.get(service, 0) + 1
        return self._counts[service] >= self.threshold

    def get_count(self, service_name: str) -> int:
        return self._counts.get(service_name, 0)

    def reset(self, service_name: str) -> None:
        self._counts[service_name] = 0


class ConsoleAlertChannel:
    def __init__(self, logger_instance: Optional[logging.Logger] = None):
        self.logger = logger_instance or logger

    def send(self, alert: Alert) -> None:
        msg = (
            f"ALERT: {alert.service_name} has failed "
            f"{alert.consecutive_failures} consecutive times "
            f"(threshold: {alert.threshold}). "
            f"Status: {alert.latest_status}. Details: {alert.latest_details}"
        )
        self.logger.error(msg)


class WebhookAlertChannel:
    def __init__(self, url: str, timeout: float = 10.0, max_retries: int = 3):
        self.url = url
        self.timeout = timeout
        self.max_retries = max_retries
        self._retry_backoff = [1, 2, 4][:max_retries]

    def send(self, alert: Alert) -> None:
        payload = {
            "event": "consecutive_failure_alert",
            "service": alert.service_name,
            "consecutive_failures": alert.consecutive_failures,
            "threshold": alert.threshold,
            "status": str(alert.latest_status.value)
            if hasattr(alert.latest_status, "value")
            else str(alert.latest_status),
            "details": alert.latest_details or {},
            "timestamp": alert.timestamp.isoformat(),
        }

        for attempt, backoff in enumerate(self._retry_backoff):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(self.url, json=payload)
                    if resp.status_code < 400:
                        return
                    if resp.status_code in (400, 401, 403, 404):
                        return
            except httpx.RequestError:
                pass

            if attempt < len(self._retry_backoff) - 1:
                time.sleep(backoff)


class NotificationHistory:
    def __init__(self, max_size: int = 1000):
        self._records: deque[Alert] = deque(maxlen=max_size)
        self._total: int = 0

    def record(self, alert: Alert) -> None:
        self._records.append(alert)
        self._total += 1

    def get_recent(self, n: int = 50) -> list[Alert]:
        items = list(self._records)
        items.reverse()
        return items[:n]

    def get_for_service(self, service_name: str) -> list[Alert]:
        return [a for a in self._records if a.service_name == service_name]

    def get_failures(self) -> list[Alert]:
        return [a for a in self._records if a.latest_status != HealthStatus.HEALTHY]

    def total_count(self) -> int:
        return self._total


class HealthAlerter:
    def __init__(
        self,
        channels: list[AlertChannel],
        threshold: int = 3,
        history_max_size: int = 1000,
    ):
        self.tracker = ConsecutiveFailureTracker(threshold=threshold)
        self.channels = channels
        self.history = NotificationHistory(max_size=history_max_size)

    def process_result(self, result: HealthResult) -> Optional[Alert]:
        should_alert = self.tracker.record(result)
        if not should_alert:
            return None

        alert = Alert(
            service_name=result.service_name,
            consecutive_failures=self.tracker.get_count(result.service_name),
            threshold=self.tracker.threshold,
            latest_status=result.status,
            latest_details=result.details,
        )

        for channel in self.channels:
            try:
                channel.send(alert)
            except Exception:
                logger.exception("Channel %s failed to send alert", type(channel).__name__)

        self.history.record(alert)
        return alert
