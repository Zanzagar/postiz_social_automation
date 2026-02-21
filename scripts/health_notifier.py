"""State transition detection and webhook notification for health monitoring."""

import os
import time
from datetime import datetime, timezone
from typing import Optional

import httpx

from health_checker import HealthResult
from health_storage import HealthStorage

WEBHOOK_URL = os.getenv("HEALTH_WEBHOOK_URL", "")
STACK_NAME = "postiz-social-automation"
MAX_RETRIES = 3
RETRY_BACKOFF = [1, 2, 4]


class HealthNotifier:
    def __init__(self, storage: HealthStorage, webhook_url: str = WEBHOOK_URL):
        self.storage = storage
        self.webhook_url = webhook_url

    def process_result(self, result: HealthResult) -> Optional[int]:
        """Process a health check result. Returns transition ID if state changed."""
        current_status = result.status.value
        previous_status = self.storage.get_last_status(result.service_name)

        self.storage.record_check(
            service_name=result.service_name,
            status=current_status,
            response_time_ms=result.response_time_ms,
            details=result.details,
        )

        if previous_status is None or previous_status == current_status:
            return None

        transition_id = self.storage.record_transition(
            service_name=result.service_name,
            from_status=previous_status,
            to_status=current_status,
        )

        if self.webhook_url:
            success = self.send_webhook(
                service_name=result.service_name,
                from_status=previous_status,
                to_status=current_status,
                details=result.details,
            )
            if success:
                self.storage.mark_webhook_sent(transition_id)

        return transition_id

    def send_webhook(
        self,
        service_name: str,
        from_status: str,
        to_status: str,
        details: Optional[dict],
    ) -> bool:
        """Send webhook notification with retry logic."""
        payload = {
            "event": "service_status_change",
            "service": service_name,
            "from_status": from_status,
            "to_status": to_status,
            "details": details.get("error", "") if details else "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stack": STACK_NAME,
        }

        for attempt, backoff in enumerate(RETRY_BACKOFF):
            try:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(self.webhook_url, json=payload)
                    if resp.status_code < 400:
                        return True
                    if resp.status_code in (400, 401, 403, 404):
                        return False
            except httpx.RequestError:
                pass

            if attempt < len(RETRY_BACKOFF) - 1:
                time.sleep(backoff)

        return False
