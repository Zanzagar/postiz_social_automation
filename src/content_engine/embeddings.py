"""Embedding-based semantic search for knowledge base.

Uses sqlite-vec for vector similarity search when available.
Falls back gracefully when sqlite-vec or sentence-transformers
are not installed — returns empty results.

Enable/disable via SQLITE_VEC_ENABLED env var (default: auto-detect).
"""

import logging
import os
import sqlite3

logger = logging.getLogger(__name__)


def is_vec_available() -> bool:
    """Check if sqlite-vec can be loaded at runtime."""
    env = os.environ.get("SQLITE_VEC_ENABLED", "").lower()
    if env == "false":
        return False
    if env == "true":
        return True

    try:
        import sqlite_vec

        conn = sqlite3.connect(":memory:")
        sqlite_vec.load(conn)
        conn.close()
        return True
    except Exception:
        return False


# Module-level flag (checked once at import time)
VEC_AVAILABLE = is_vec_available()

if VEC_AVAILABLE:
    logger.info("sqlite-vec is available for embedding search")
else:
    logger.info("sqlite-vec not available — embedding search disabled, FTS5 will be used instead")


def _get_embedding(text: str) -> list[float] | None:
    """Generate embedding for text using sentence-transformers.

    Returns None if sentence-transformers is not installed.
    """
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("all-MiniLM-L6-v2")
        return model.encode(text).tolist()
    except ImportError:
        logger.debug("sentence-transformers not installed")
        return None
    except Exception as e:
        logger.warning("Embedding generation failed: %s", e)
        return None


def _vec_search(
    db_path: str,
    query: str,
    pillar: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Search knowledge base using vector similarity.

    Returns empty list if sqlite-vec is unavailable or disabled.
    """
    # Check env var override (allows runtime disable)
    env = os.environ.get("SQLITE_VEC_ENABLED", "").lower()
    if env == "false":
        return []

    if not VEC_AVAILABLE:
        return []

    embedding = _get_embedding(query)
    if embedding is None:
        return []

    try:
        import struct

        import sqlite_vec

        conn = sqlite3.connect(db_path)
        sqlite_vec.load(conn)
        conn.row_factory = sqlite3.Row

        # Serialize embedding to bytes
        query_vec = struct.pack(f"{len(embedding)}f", *embedding)

        if pillar:
            rows = conn.execute(
                """
                SELECT wk.id, wk.fact_type, wk.content, wk.pillar,
                       distance
                FROM web_knowledge_vec v
                JOIN web_knowledge wk ON wk.id = v.rowid
                WHERE v.embedding MATCH ?
                  AND wk.pillar = ?
                ORDER BY distance
                LIMIT ?
                """,
                (query_vec, pillar, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT wk.id, wk.fact_type, wk.content, wk.pillar,
                       distance
                FROM web_knowledge_vec v
                JOIN web_knowledge wk ON wk.id = v.rowid
                WHERE v.embedding MATCH ?
                ORDER BY distance
                LIMIT ?
                """,
                (query_vec, limit),
            ).fetchall()

        conn.close()
        return [
            {
                "id": r["id"],
                "fact_type": r["fact_type"],
                "content": r["content"],
                "pillar": r["pillar"],
                "score": -r["distance"],  # Negate: lower distance = higher score
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning("Vec search failed: %s", e)
        return []
