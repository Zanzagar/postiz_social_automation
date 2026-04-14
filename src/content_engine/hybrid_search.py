"""Reciprocal Rank Fusion for combining FTS5 and vector search results.

Combines ranked lists from multiple search methods into a single
relevance-ordered result set. When only FTS5 is available (sqlite-vec
not installed), hybrid_search degrades to FTS-only search.
"""

import logging

from content_engine.crawlers.knowledge_context import _fts_search
from content_engine.embeddings import _vec_search

logger = logging.getLogger(__name__)

# RRF constant k — higher values give more weight to lower-ranked items
RRF_K = 60


def reciprocal_rank_fusion(
    ranked_lists: list[list[dict]],
    limit: int = 10,
    k: int = RRF_K,
) -> list[dict]:
    """Combine multiple ranked result lists using RRF.

    Each item must have an 'id' key for deduplication.
    Returns items sorted by combined RRF score (descending).
    """
    scores: dict[int, float] = {}
    items: dict[int, dict] = {}

    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list, start=1):
            item_id = item.get("id", id(item))
            scores[item_id] = scores.get(item_id, 0) + 1.0 / (k + rank)
            if item_id not in items:
                items[item_id] = item

    # Sort by score descending
    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    results = []
    for item_id in sorted_ids[:limit]:
        item = items[item_id].copy()
        item["rrf_score"] = scores[item_id]
        results.append(item)

    return results


def hybrid_search(
    db_path: str,
    query: str,
    pillar: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Search knowledge base using FTS5 + vec, fused via RRF.

    Falls back to FTS-only when sqlite-vec is unavailable.
    """
    if not query or not query.strip():
        return []

    ranked_lists = []

    # FTS5 search (always available)
    fts_results = _fts_search(db_path, query, pillar=pillar, limit=limit)
    if fts_results:
        ranked_lists.append(fts_results)

    # Vector search (when available)
    vec_results = _vec_search(db_path, query, pillar=pillar, limit=limit)
    if vec_results:
        ranked_lists.append(vec_results)

    if not ranked_lists:
        return []

    return reciprocal_rank_fusion(ranked_lists, limit=limit)
