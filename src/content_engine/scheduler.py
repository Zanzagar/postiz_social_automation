"""Scheduling logic for content pipeline execution.

Uses the `schedule` library for cron-like job scheduling of
enhance, suggest, and learn pipelines.
"""

import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import schedule

logger = logging.getLogger(__name__)

SCRIPTS_DIR = Path(__file__).parent / "scripts"


def run_pipeline(name: str) -> bool:
    """Run a pipeline script by name (enhance, suggest, learn).

    Returns True on success, False on failure.
    """
    script = SCRIPTS_DIR / f"run_{name}.py"
    logger.info("Starting %s pipeline: %s", name, script)
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.error("%s pipeline failed (exit %d): %s", name, result.returncode, result.stderr)
            return False
        logger.info("%s pipeline completed", name)
        return True
    except Exception:
        logger.exception("Failed to execute %s pipeline", name)
        return False


def build_schedule(
    *,
    enhance_minutes: int = 30,
    suggest_day: str = "sunday",
    suggest_time: str = "09:00",
    learn_time: str = "06:00",
) -> schedule.Scheduler:
    """Build a scheduler with default or custom intervals.

    Args:
        enhance_minutes: How often to run enhance (minutes).
        suggest_day: Day of week for suggestions.
        suggest_time: Time for weekly suggestions (HH:MM).
        learn_time: Time for daily learning (HH:MM).
    """
    sched = schedule.Scheduler()

    sched.every(enhance_minutes).minutes.do(run_pipeline, "enhance").tag("enhance")

    getattr(sched.every(), suggest_day).at(suggest_time).do(run_pipeline, "suggest").tag("suggest")

    sched.every().day.at(learn_time).do(run_pipeline, "learn").tag("learn")

    return sched


def main() -> None:
    """Entry point for the scheduler daemon."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    sched = build_schedule()
    logger.info(
        "Scheduler started with %d jobs: %s",
        len(sched.get_jobs()),
        ", ".join(t for j in sched.get_jobs() for t in j.tags),
    )

    while True:
        sched.run_pending()
        time.sleep(60)


class CrawlScheduler:
    """Manages periodic execution of crawl and analytics jobs via state file."""

    def __init__(
        self,
        db_path: str,
        state_dir: Path | None = None,
        web_crawl_interval_hours: int = 168,
        analytics_sync_interval_hours: int = 24,
        hashtag_update_interval_hours: int = 24,
    ):
        self.db_path = db_path
        self.web_crawl_interval_hours = web_crawl_interval_hours
        self.analytics_sync_interval_hours = analytics_sync_interval_hours
        self.hashtag_update_interval_hours = hashtag_update_interval_hours

        if state_dir is None:
            state_dir = Path("data")
        self._state_file = state_dir / "scheduler_state.json"

    def _load_state(self) -> dict:
        if not self._state_file.exists():
            return {}
        try:
            return json.loads(self._state_file.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_state(self, state: dict) -> None:
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        self._state_file.write_text(json.dumps(state, indent=2))

    def record_run(self, job_name: str) -> None:
        """Record that a job ran at the current time."""
        state = self._load_state()
        state[job_name] = datetime.now(timezone.utc).isoformat()
        self._save_state(state)

    def should_run(self, job_name: str) -> bool:
        """Check if a job should run based on its interval."""
        state = self._load_state()
        last_run = state.get(job_name)
        if not last_run:
            return True

        intervals = {
            "web_crawl": self.web_crawl_interval_hours,
            "analytics_sync": self.analytics_sync_interval_hours,
            "hashtag_update": self.hashtag_update_interval_hours,
        }
        interval = intervals.get(job_name, 24)

        last_dt = datetime.fromisoformat(last_run)
        elapsed = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
        return elapsed >= interval


if __name__ == "__main__":
    main()
