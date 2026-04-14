"""Preference pairs from edit history for prompt injection.

Stores original/edited caption pairs to learn user preferences.
Retrieval provides few-shot examples of desired editing behavior.
"""

import logging
import sqlite3
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


def save_preference_pair(
    db_path: str,
    original: str,
    edited: str,
    platform: str,
    instruction: str | None = None,
) -> bool:
    """Save an original→edited pair from user iteration."""
    try:
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO preference_pairs "
            "(platform, original_text, edited_text, instruction, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (platform, original, edited, instruction, datetime.now(UTC).isoformat()),
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.OperationalError:
        logger.warning("preference_pairs table not available")
        return False


def get_preference_pairs(
    db_path: str,
    platform: str | None = None,
    limit: int = 5,
) -> list[dict]:
    """Retrieve recent preference pairs for prompt injection."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
    except (sqlite3.OperationalError, sqlite3.DatabaseError):
        return []

    try:
        if platform:
            rows = conn.execute(
                "SELECT platform, original_text, edited_text, instruction "
                "FROM preference_pairs WHERE platform = ? "
                "ORDER BY created_at DESC LIMIT ?",
                (platform, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT platform, original_text, edited_text, instruction "
                "FROM preference_pairs "
                "ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    except sqlite3.OperationalError:
        conn.close()
        return []

    conn.close()
    return [dict(r) for r in rows]
