"""Knowledge context builder for caption generation prompts.

Queries the knowledge base to build context strings that get injected
into Claude prompts during caption generation. Uses FTS5 for relevance-
ranked search when available, falls back to simple LIMIT queries.
"""

import logging
import re
import sqlite3

logger = logging.getLogger(__name__)

# Common English stopwords to skip during keyword extraction
_STOPWORDS = frozenset(
    "a an the is are was were be been being have has had do does did "
    "will would shall should may might can could of in on at to for "
    "with by from as into through during before after above below "
    "between out off over under again further then once here there "
    "when where why how all both each few more most other some such "
    "no nor not only own same so than too very and but or if while "
    "about also just because its it this that these those he she they "
    "we you i my your his her our their what which who whom me him us "
    "them am".split()
)


def _extract_keywords(text: str) -> list[str]:
    """Extract meaningful keywords from text for FTS queries.

    Simple tokenization: lowercase, remove punctuation, filter stopwords,
    deduplicate while preserving order.
    """
    if not text:
        return []
    words = re.findall(r"[a-zA-Z]+", text.lower())
    seen: set[str] = set()
    result: list[str] = []
    for w in words:
        if w not in _STOPWORDS and w not in seen and len(w) > 1:
            seen.add(w)
            result.append(w)
    return result


def _fts_search(
    db_path: str,
    query: str,
    pillar: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Search knowledge base using FTS5 with BM25 ranking.

    Returns list of dicts with keys: id, fact_type, content, pillar, score.
    Returns empty list if FTS table doesn't exist.
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
    except (sqlite3.OperationalError, sqlite3.DatabaseError):
        return []

    # Build FTS5 match expression from keywords
    keywords = _extract_keywords(query)
    if not keywords:
        conn.close()
        return []

    # Use OR to match any keyword (more flexible than AND)
    match_expr = " OR ".join(keywords)

    try:
        if pillar:
            rows = conn.execute(
                """
                SELECT wk.id, wk.fact_type, wk.content, wk.pillar,
                       rank AS score
                FROM web_knowledge_fts fts
                JOIN web_knowledge wk ON wk.id = fts.rowid
                WHERE web_knowledge_fts MATCH ?
                  AND wk.pillar = ?
                ORDER BY rank
                LIMIT ?
                """,
                (match_expr, pillar, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT wk.id, wk.fact_type, wk.content, wk.pillar,
                       rank AS score
                FROM web_knowledge_fts fts
                JOIN web_knowledge wk ON wk.id = fts.rowid
                WHERE web_knowledge_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (match_expr, limit),
            ).fetchall()
    except sqlite3.OperationalError:
        # FTS table doesn't exist or query error
        conn.close()
        return []

    conn.close()
    return [dict(r) for r in rows]


def get_knowledge_context(
    db_path: str,
    pillar: str | None = None,
    raw_text: str | None = None,
    max_facts: int = 5,
    max_chars: int = 2000,
) -> str:
    """Build a knowledge context string for prompt injection.

    Uses FTS5 search when available (relevance-ranked by BM25).
    Falls back to simple LIMIT query if FTS table is missing.

    Args:
        db_path: Path to the SQLite database.
        pillar: Optional pillar to filter by.
        raw_text: Optional raw text to extract search keywords from.
        max_facts: Maximum number of knowledge facts to include.
        max_chars: Approximate character budget for the context.

    Returns:
        A formatted string ready to inject into a Claude prompt,
        or "" if the database is unavailable.
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
    except (sqlite3.OperationalError, sqlite3.DatabaseError):
        return ""

    parts: list[str] = []
    char_count = 0

    # --- Knowledge facts ---
    # Try FTS search first (if raw_text provided and FTS table exists)
    facts: list = []
    if raw_text:
        fts_results = _fts_search(db_path, raw_text, pillar=pillar, limit=max_facts)
        if fts_results:
            facts = fts_results

    # Fall back to simple LIMIT query
    if not facts:
        try:
            if pillar:
                facts = conn.execute(
                    """SELECT fact_type, content, pillar
                       FROM web_knowledge
                       WHERE pillar = ?
                       AND content IS NOT NULL AND length(content) > 20
                       AND content NOT LIKE '%shopping cart%'
                       AND content NOT LIKE '%page is a%'
                       LIMIT ?""",
                    (pillar, max_facts),
                ).fetchall()
            if not facts:
                facts = conn.execute(
                    """SELECT fact_type, content, pillar
                       FROM web_knowledge
                       WHERE content IS NOT NULL AND length(content) > 20
                       AND content NOT LIKE '%shopping cart%'
                       AND content NOT LIKE '%page is a%'
                       LIMIT ?""",
                    (max_facts,),
                ).fetchall()
        except sqlite3.OperationalError:
            pass

    if facts:
        parts.append("BACKGROUND (use only if naturally relevant — don't force facts in):")
        for fact in facts:
            ft = (
                fact.get("fact_type", fact["fact_type"])
                if isinstance(fact, dict)
                else fact["fact_type"]
            )
            content = fact.get("content", "") if isinstance(fact, dict) else fact["content"]
            line = f"- [{ft}] {content}"
            if char_count + len(line) > max_chars:
                break
            parts.append(line)
            char_count += len(line)
        parts.append("")

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
