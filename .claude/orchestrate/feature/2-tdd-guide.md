## TDD Guide Report

### Objective
Add an alerting module that sends notifications when a health check fails consecutively 3 times. Support webhook (HTTP POST) and console logging as notification channels. Include a notification history tracker.

### Summary
Wrote complete test file `tests/test_health_alerter.py` with 60 tests across 7 test classes, following existing codebase patterns (class-based pytest, MagicMock, @patch for httpx).

### Test Structure
| Test Class | Count | Component |
|------------|-------|-----------|
| TestAlertDataclass | 3 | Alert dataclass fields |
| TestAlertChannelProtocol | 2 | Protocol runtime checking |
| TestConsecutiveFailureTracker | 14 | Core counting logic |
| TestConsoleAlertChannel | 6 | Console logging channel |
| TestWebhookAlertChannel | 10 | HTTP POST with retry |
| TestNotificationHistory | 11 | Bounded history buffer |
| TestHealthAlerter | 18 | Full orchestrator integration |

### Key Test Cases
- Threshold boundary: exactly at, below, and above threshold
- Counter reset on healthy result
- Multi-service independence
- Webhook retry on network error, no retry on 4xx
- History eviction with deque(maxlen)
- Channel exception isolation
- Return value contract (Alert or None)

### Recommended Implementation Order (RED → GREEN)
1. Alert dataclass + AlertChannel Protocol
2. ConsecutiveFailureTracker
3. ConsoleAlertChannel
4. WebhookAlertChannel
5. NotificationHistory
6. HealthAlerter orchestrator

### Context for Next Agent
- Test file at: `tests/test_health_alerter.py`
- 60 tests, all currently failing (ImportError — module doesn't exist yet)
- Tests use `@patch("health_alerter.httpx")` and `@patch("health_alerter.time")` for mocking
- Tests expect `tracker.record()` to accept HealthResult directly (not separate args)
- Tests expect `history.record()` to accept just an Alert (no channel_name/success)
- Tests expect alerts to fire on every call >= threshold (not just exactly at threshold)

### Evaluation
Cycles needed: 1 | Gaps remaining: none
