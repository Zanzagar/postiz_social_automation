"""Rate limiting for Claude CLI calls.

Prevents overload during parallel generation by limiting concurrent
subprocess calls via a threading semaphore.
"""

import logging
import os
import threading
from contextlib import contextmanager

logger = logging.getLogger(__name__)

_DEFAULT_MAX_CONCURRENT = 3
_semaphore: threading.Semaphore | None = None
_lock = threading.Lock()


def _get_max_concurrent() -> int:
    """Read max concurrent from env, default 3."""
    val = os.environ.get("CLAUDE_MAX_CONCURRENT", "")
    try:
        return int(val) if val else _DEFAULT_MAX_CONCURRENT
    except ValueError:
        return _DEFAULT_MAX_CONCURRENT


def _get_semaphore() -> threading.Semaphore:
    """Lazy-init semaphore (allows env var to be set after import)."""
    global _semaphore
    if _semaphore is None:
        with _lock:
            if _semaphore is None:
                _semaphore = threading.Semaphore(_get_max_concurrent())
    return _semaphore


@contextmanager
def rate_limit_sync():
    """Context manager that limits concurrent Claude CLI calls."""
    sem = _get_semaphore()
    logger.debug("Waiting for rate limit slot...")
    sem.acquire()
    try:
        yield
    finally:
        sem.release()
