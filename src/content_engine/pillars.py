"""Dynamic pillar loading from SQLite database.

Provides a sync interface for the content engine to read active pillar names
from the pillars table, replacing the hardcoded ContentPillar enum.
"""

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "gvsa.db"

# Fallback pillar names when database is unavailable
_FALLBACK_PILLARS = ["Cow Life", "Farm Ops", "Community", "Kitchen", "Spiritual", "CTA"]


def get_active_pillar_names(db_path: Path | str | None = None) -> list[str]:
    """Return active pillar names from the database.

    Falls back to a default list if the database or table doesn't exist.
    This is a synchronous call suitable for the content engine.
    """
    if db_path is None:
        db_path = _DEFAULT_DB_PATH

    db_path = Path(db_path)
    if not db_path.exists():
        logger.debug("Database not found at %s, using fallback pillars", db_path)
        return list(_FALLBACK_PILLARS)

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute(
            "SELECT name FROM pillars WHERE is_active = 1 ORDER BY sort_order, name"
        )
        names = [row[0] for row in cursor.fetchall()]
        conn.close()
        if not names:
            logger.debug("No active pillars in database, using fallback")
            return list(_FALLBACK_PILLARS)
        return names
    except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
        logger.warning("Failed to load pillars from database: %s", e)
        return list(_FALLBACK_PILLARS)
