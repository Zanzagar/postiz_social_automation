"""Knowledge context builder for caption generation prompts.

Queries the knowledge base and social history to build context strings
that get injected into Claude prompts during caption generation.
"""

import logging
import sqlite3

logger = logging.getLogger(__name__)


def get_knowledge_context(
    db_path: str,
    pillar: str | None = None,
    max_facts: int = 10,
    max_examples: int = 3,
    max_chars: int = 2000,
) -> str:
    """Build a knowledge context string for prompt injection.

    Args:
        db_path: Path to the SQLite database.
        pillar: Optional pillar to filter by. If None, returns all.
        max_facts: Maximum number of knowledge facts to include.
        max_examples: Maximum number of social post examples to include.
        max_chars: Approximate character budget for the context.

    Returns:
        A formatted string ready to inject into a Claude prompt, or "" if
        the database is unavailable.
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
    except (sqlite3.OperationalError, sqlite3.DatabaseError):
        return ""

    parts: list[str] = []
    char_count = 0

    # --- Knowledge facts ---
    try:
        if pillar:
            facts = conn.execute(
                "SELECT fact_type, content FROM web_knowledge WHERE pillar = ? LIMIT ?",
                (pillar, max_facts),
            ).fetchall()
        else:
            facts = conn.execute(
                "SELECT fact_type, content FROM web_knowledge LIMIT ?",
                (max_facts,),
            ).fetchall()

        if facts:
            parts.append("KNOWLEDGE BASE FACTS:")
            for fact in facts:
                line = f"- [{fact['fact_type']}] {fact['content']}"
                if char_count + len(line) > max_chars:
                    break
                parts.append(line)
                char_count += len(line)
            parts.append("")
    except sqlite3.OperationalError:
        pass

    # --- Social history examples (high-engagement) ---
    try:
        if pillar:
            examples = conn.execute(
                """SELECT post_text, platform, likes + comments + shares as engagement
                   FROM social_history
                   WHERE pillar = ? AND post_text IS NOT NULL AND post_text != ''
                   ORDER BY engagement DESC LIMIT ?""",
                (pillar, max_examples),
            ).fetchall()
        else:
            examples = conn.execute(
                """SELECT post_text, platform, likes + comments + shares as engagement
                   FROM social_history
                   WHERE post_text IS NOT NULL AND post_text != ''
                   ORDER BY engagement DESC LIMIT ?""",
                (max_examples,),
            ).fetchall()

        if examples:
            parts.append("HIGH-PERFORMING POST EXAMPLES:")
            for ex in examples:
                line = (
                    f"- [{ex['platform']}, {ex['engagement']} engagements] {ex['post_text'][:200]}"
                )
                if char_count + len(line) > max_chars:
                    break
                parts.append(line)
                char_count += len(line)
            parts.append("")
    except sqlite3.OperationalError:
        pass

    # --- Top-performing hashtags ---
    try:
        hashtag_rows = conn.execute(
            """SELECT hashtag, avg_engagement
               FROM hashtag_performance
               ORDER BY avg_engagement DESC LIMIT 10"""
        ).fetchall()

        if hashtag_rows:
            tags = [f"#{r['hashtag']} (avg {r['avg_engagement']:.0f})" for r in hashtag_rows]
            line = "SUGGESTED HASHTAGS: " + ", ".join(tags)
            if char_count + len(line) <= max_chars:
                parts.append(line)
                parts.append("")
    except sqlite3.OperationalError:
        pass

    conn.close()
    return "\n".join(parts)
