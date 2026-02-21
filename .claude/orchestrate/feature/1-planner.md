## Planner Report

### Objective
Add an alerting module that sends notifications when a health check fails consecutively 3 times. Support webhook (HTTP POST) and console logging as notification channels. Include a notification history tracker.

### Summary
Planned a new `health_alerter.py` module with 7 components: `AlertChannel` protocol, `Alert` dataclass, `ConsecutiveFailureTracker`, `WebhookAlertChannel`, `ConsoleAlertChannel`, `NotificationHistory`, and `HealthAlerter` orchestrator. The module integrates between the existing notifier and monitor layers.

### Findings

**Architecture**:
- New file: `scripts/health_alerter.py` — all alerting logic
- New file: `tests/test_health_alerter.py` — ~25-30 test cases
- Modified: `scripts/health_monitor.py` — wire alerter into run_once/run_continuous
- Modified: `tests/test_health_monitor.py` — integration tests

**Key Design Decisions**:
1. `Protocol` (not ABC) for `AlertChannel` — matches existing duck-typing style
2. Alert fires only when count **equals** threshold (not every subsequent failure) — prevents alert fatigue
3. In-memory tracker (not SQLite) — ephemeral state, safe default on restart
4. `deque(maxlen=1000)` for history — bounded without manual cleanup
5. Both UNHEALTHY and MISSING statuses count as failures

**Risks Identified**:
- LOW: Counter state lost on restart (acceptable)
- LOW: Alert storm from multiple services (7 max, acceptable)
- LOW: Webhook failures during alerting (retry + console fallback)
- LOW: History memory growth (bounded deque)
- MEDIUM: Single alert vs recurring alerts (deferred — extensible later)

### Recommendations
1. Implement TDD: write tests first for ConsecutiveFailureTracker, then channels, then history, then HealthAlerter
2. Mock httpx for webhook tests (same pattern as test_health_notifier.py)
3. Keep integration with health_monitor.py minimal — just add `alerter.process_result()` call
4. Configure via env vars: `HEALTH_ALERT_THRESHOLD`, `HEALTH_ALERT_WEBHOOK_URL`

### Context for Next Agent
- File to create: `scripts/health_alerter.py` with classes listed above
- Tests to create: `tests/test_health_alerter.py` with 7 test classes
- Existing patterns: `test_health_notifier.py` uses `@patch("health_notifier.httpx")` for webhook mocking
- HealthResult has: service_name, status (HealthStatus enum), response_time_ms, details (dict)
- HealthStatus enum: HEALTHY, UNHEALTHY, MISSING

### Evaluation
Cycles needed: 1 | Gaps remaining: none
