"""Base classes for crawl checkpoint and error handling."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class CrawlCheckpoint:
    """File-based checkpoint for resumable crawls."""

    def __init__(self, source: str, data_dir: Path | None = None):
        self.source = source
        if data_dir is None:
            data_dir = Path("data")
        self._path = data_dir / f"crawl_checkpoint_{source}.json"

    def save(self, last_url: str, processed_count: int) -> None:
        """Save checkpoint to disk."""
        data = {
            "source": self.source,
            "last_url": last_url,
            "processed_count": processed_count,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(data, indent=2))

    def load(self) -> dict:
        """Load checkpoint from disk. Returns empty dict if not found."""
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    def clear(self) -> None:
        """Delete checkpoint file."""
        if self._path.exists():
            self._path.unlink()


@dataclass
class CrawlResult:
    """Result of a crawl operation."""

    source: str
    total: int
    succeeded: int
    failed: int
    errors: list[str] = field(default_factory=list)

    @property
    def is_success(self) -> bool:
        return self.failed == 0

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "total": self.total,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "is_success": self.is_success,
            "errors": self.errors,
        }
