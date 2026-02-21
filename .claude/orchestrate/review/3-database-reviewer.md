## Database Reviewer Report

### Objective
Review SQLite storage layer for query efficiency, connection handling, schema design, and operational patterns.

### Summary
Reviewed `health_storage.py` and `test_storage.py`. Found 0 CRITICAL, 0 HIGH, 3 MEDIUM, and 3 LOW findings. Schema design is fundamentally sound with correct parameterization and appropriate indexes. Main issues are connection lifecycle (per-call churn), missing WAL mode, and a details deserialization bug.

### Findings

**MEDIUM**
1. **health_storage.py:14-17** — Per-call connection churn: Every public method opens and closes its own SQLite connection. For a 60-second monitoring loop across 7 services, this means ~21 connect/disconnect cycles per minute. Recommendation: Hold persistent connection with `__enter__`/`__exit__` lifecycle.

2. **health_storage.py:19-45** — WAL mode not enabled: Default rollback journal mode causes exclusive locks on every write. Any concurrent reader (separate process querying history) gets SQLITE_BUSY. Recommendation: Add `PRAGMA journal_mode = WAL; PRAGMA synchronous = NORMAL;` to schema init.

3. **health_storage.py:101-117** — `get_history` returns `details` as raw JSON string instead of deserialized dict. Callers get `{"details": "{\"docker_health\": \"healthy\"}"}` instead of nested dict. `row_factory` usage is also inconsistent across methods.

**LOW**
4. **health_storage.py:23** — Missing `checked_at`-first index for `get_uptime_stats`. Existing composite `(service_name, checked_at)` doesn't serve the time-range-first aggregation query.

5. **health_storage.py:108** — No validation on `hours`/`days` parameters. Zero or negative values produce semantically wrong time strings.

6. **health_storage.py:29,41** — Missing NOT NULL on timestamp columns (`checked_at`, `transitioned_at`). DEFAULT CURRENT_TIMESTAMP prevents NULLs in practice, but schema doesn't enforce it.

### Test Coverage Observations
- No test for `details` deserialization (would catch finding #3 immediately)
- No multi-service test for `get_uptime_stats` GROUP BY correctness
- `test_returns_most_recent_status` relies on insertion order within same-second timestamps (non-deterministic with `CURRENT_TIMESTAMP` second granularity)

### Schema Assessment
The schema is otherwise well-designed:
- Parameterized queries throughout (no injection risk)
- `INTEGER PRIMARY KEY AUTOINCREMENT` correctly used
- Composite index `(service_name, checked_at)` correctly ordered for dominant query
- `IF NOT EXISTS` guards make initialization idempotent

### Recommendations
1. Enable WAL mode + persistent connection (biggest single improvement)
2. Fix `details` JSON deserialization on read path
3. Add `checked_at`-first index for aggregation queries
4. Add NOT NULL constraints to timestamp columns

### Evaluation
Cycles needed: 1 | Gaps remaining: none
