"""Hashtag performance tracking and suggestion engine."""

import json
import logging
import sqlite3
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class HashtagTracker:
    """Track hashtag performance across platforms and suggest high-performers."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def update_performance(self) -> None:
        """Recompute hashtag_performance from social_history data."""
        conn = self._connect()

        # Get all posts with hashtags
        rows = conn.execute(
            "SELECT platform, hashtags, likes, comments, shares FROM social_history WHERE hashtags IS NOT NULL"
        ).fetchall()

        # Aggregate per (hashtag, platform)
        stats: dict[tuple[str, str], dict] = {}
        for row in rows:
            try:
                hashtags = json.loads(row["hashtags"])
            except (json.JSONDecodeError, TypeError):
                continue

            engagement = (row["likes"] or 0) + (row["comments"] or 0) + (row["shares"] or 0)
            platform = row["platform"]

            for tag in hashtags:
                key = (tag, platform)
                if key not in stats:
                    stats[key] = {"times_used": 0, "total_engagement": 0}
                stats[key]["times_used"] += 1
                stats[key]["total_engagement"] += engagement

        # Upsert into hashtag_performance
        now = datetime.now(timezone.utc).isoformat()
        for (hashtag, platform), data in stats.items():
            avg = data["total_engagement"] / data["times_used"] if data["times_used"] > 0 else 0
            conn.execute(
                """INSERT INTO hashtag_performance (hashtag, platform, times_used, total_engagement, avg_engagement, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(hashtag, platform)
                   DO UPDATE SET times_used = ?, total_engagement = ?, avg_engagement = ?, updated_at = ?""",
                (
                    hashtag,
                    platform,
                    data["times_used"],
                    data["total_engagement"],
                    avg,
                    now,
                    data["times_used"],
                    data["total_engagement"],
                    avg,
                    now,
                ),
            )

        conn.commit()
        conn.close()

    def get_top_hashtags(self, platform: str | None = None, limit: int = 20) -> list[dict]:
        """Return top hashtags by total engagement."""
        conn = self._connect()
        if platform:
            rows = conn.execute(
                """SELECT * FROM hashtag_performance
                   WHERE platform = ? ORDER BY total_engagement DESC LIMIT ?""",
                (platform, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM hashtag_performance ORDER BY total_engagement DESC LIMIT ?",
                (limit,),
            ).fetchall()
        conn.close()

        return [
            {
                "hashtag": r["hashtag"],
                "platform": r["platform"],
                "times_used": r["times_used"],
                "total_engagement": r["total_engagement"],
                "avg_engagement": r["avg_engagement"],
                "trend": r["trend"],
            }
            for r in rows
        ]

    def suggest_hashtags(self, platform: str, count: int = 5) -> list[str]:
        """Return top hashtag names for a platform, sorted by avg engagement."""
        conn = self._connect()
        rows = conn.execute(
            """SELECT hashtag FROM hashtag_performance
               WHERE platform = ? AND times_used >= 1
               ORDER BY avg_engagement DESC LIMIT ?""",
            (platform, count),
        ).fetchall()
        conn.close()
        return [r["hashtag"] for r in rows]
