"""Tests for Claude CLI rate limiter."""

import threading
import time

from content_engine.rate_limiter import _get_max_concurrent, rate_limit_sync


class TestSyncRateLimiter:
    def test_allows_within_limit(self):
        """Single call completes without blocking."""
        with rate_limit_sync():
            pass  # Should not block

    def test_limits_concurrent_calls(self):
        """Only max_concurrent calls run at once."""
        max_c = _get_max_concurrent()
        peak = [0]
        current = [0]
        lock = threading.Lock()

        def worker():
            with rate_limit_sync():
                with lock:
                    current[0] += 1
                    peak[0] = max(peak[0], current[0])
                time.sleep(0.05)
                with lock:
                    current[0] -= 1

        threads = [threading.Thread(target=worker) for _ in range(max_c + 2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert peak[0] <= max_c

    def test_all_calls_complete(self):
        """All queued calls eventually complete."""
        results = []

        def worker(i):
            with rate_limit_sync():
                time.sleep(0.01)
                results.append(i)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(results) == 6


class TestConfig:
    def test_default_max_concurrent(self):
        assert _get_max_concurrent() == 3

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("CLAUDE_MAX_CONCURRENT", "5")
        assert _get_max_concurrent() == 5

    def test_invalid_env_falls_back(self, monkeypatch):
        monkeypatch.setenv("CLAUDE_MAX_CONCURRENT", "bad")
        assert _get_max_concurrent() == 3
