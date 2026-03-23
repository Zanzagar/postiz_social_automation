"""Analytics correlation engine — overview, pillar breakdown, top posts."""

import logging
import sqlite3

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """Queries analytics_cache + content_rows for dashboards and insights."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_overview(self) -> dict:
        """Return aggregate analytics overview."""
        conn = self._connect()
        row = conn.execute("""
            SELECT
                COUNT(DISTINCT ac.content_row_id) as total_posts,
                SUM(ac.likes + ac.comments + ac.shares) as total_engagement,
                AVG(ac.likes + ac.comments + ac.shares) as avg_engagement,
                SUM(ac.reach) as total_reach,
                SUM(ac.impressions) as total_impressions
            FROM analytics_cache ac
        """).fetchone()
        conn.close()

        return {
            "total_posts": row["total_posts"] or 0,
            "total_engagement": row["total_engagement"] or 0,
            "avg_engagement": round(row["avg_engagement"] or 0, 1),
            "total_reach": row["total_reach"] or 0,
            "total_impressions": row["total_impressions"] or 0,
        }

    def get_pillar_breakdown(self) -> list[dict]:
        """Return engagement stats grouped by content pillar."""
        conn = self._connect()
        rows = conn.execute("""
            SELECT
                cr.pillar as pillar,
                COUNT(*) as post_count,
                SUM(ac.likes + ac.comments + ac.shares) as total_engagement,
                AVG(ac.likes + ac.comments + ac.shares) as avg_engagement,
                SUM(ac.reach) as total_reach
            FROM analytics_cache ac
            JOIN content_rows cr ON ac.content_row_id = cr.id
            WHERE cr.pillar IS NOT NULL
            GROUP BY cr.pillar
            ORDER BY total_engagement DESC
        """).fetchall()
        conn.close()

        return [
            {
                "pillar": r["pillar"],
                "post_count": r["post_count"],
                "total_engagement": r["total_engagement"] or 0,
                "avg_engagement": round(r["avg_engagement"] or 0, 1),
                "total_reach": r["total_reach"] or 0,
            }
            for r in rows
        ]

    def get_top_posts(self, limit: int = 10) -> list[dict]:
        """Return top posts by engagement."""
        conn = self._connect()
        rows = conn.execute(
            """
            SELECT
                cr.id,
                cr.pillar as pillar,
                cr.raw_text,
                cr.date,
                ac.platform,
                (ac.likes + ac.comments + ac.shares) as engagement,
                ac.likes,
                ac.comments,
                ac.shares,
                ac.reach
            FROM analytics_cache ac
            JOIN content_rows cr ON ac.content_row_id = cr.id
            ORDER BY engagement DESC
            LIMIT ?
        """,
            (limit,),
        ).fetchall()
        conn.close()

        return [
            {
                "id": r["id"],
                "pillar": r["pillar"],
                "raw_text": r["raw_text"][:200] if r["raw_text"] else "",
                "date": r["date"],
                "platform": r["platform"],
                "engagement": r["engagement"],
                "likes": r["likes"],
                "comments": r["comments"],
                "shares": r["shares"],
                "reach": r["reach"],
            }
            for r in rows
        ]
