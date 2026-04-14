"""Few-shot example retrieval for prompt injection.

Fetches top-engagement exemplar posts from the database,
filtered by platform and optionally by pillar.
"""

import sqlite3


def get_few_shot_examples(
    db_path: str,
    platform: str,
    pillar: str | None = None,
    limit: int = 3,
) -> list[dict]:
    """Retrieve active few-shot examples ordered by engagement.

    Returns list of dicts with keys:
    platform, pillar, raw_text, caption, engagement_score.
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
    except (sqlite3.OperationalError, sqlite3.DatabaseError):
        return []

    try:
        if pillar:
            rows = conn.execute(
                """SELECT platform, pillar, raw_text, caption,
                          engagement_score
                   FROM few_shot_examples
                   WHERE platform = ? AND pillar = ? AND is_active = 1
                   ORDER BY engagement_score DESC
                   LIMIT ?""",
                (platform, pillar, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT platform, pillar, raw_text, caption,
                          engagement_score
                   FROM few_shot_examples
                   WHERE platform = ? AND is_active = 1
                   ORDER BY engagement_score DESC
                   LIMIT ?""",
                (platform, limit),
            ).fetchall()
    except sqlite3.OperationalError:
        conn.close()
        return []

    conn.close()
    return [dict(r) for r in rows]
