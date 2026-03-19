"""Knowledge base API endpoints — crawl triggers, status, search."""

import json
import logging
import sqlite3
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Query

from api.auth import get_current_user

logger = logging.getLogger(__name__)

# In-memory crawl progress (simple approach for single-process FastAPI)
_crawl_progress: dict = {"running": False, "source": "", "current": 0, "total": 0, "phase": ""}

router = APIRouter(
    prefix="/api/knowledge", tags=["knowledge"], dependencies=[Depends(get_current_user)]
)

_DEFAULT_DB_PATH = str(Path("data/gvsa.db"))


def get_db_path() -> str:
    """Return path to SQLite database. Patchable for tests."""
    return _DEFAULT_DB_PATH


# ------------------------------------------------------------------
# GET /status — per-source crawl statistics
# ------------------------------------------------------------------


@router.get("/status")
async def get_status(db_path: str = Depends(get_db_path)):
    """Return crawl and import statistics per source."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Web page stats per site
    web_stats = conn.execute(
        """SELECT site, COUNT(*) as page_count, MAX(last_crawled) as last_crawled
           FROM web_pages GROUP BY site"""
    ).fetchall()

    # Social history stats per platform
    social_stats = conn.execute(
        """SELECT platform, COUNT(*) as post_count, MAX(imported_at) as last_imported
           FROM social_history GROUP BY platform"""
    ).fetchall()

    # Knowledge entry count
    knowledge_count = conn.execute("SELECT COUNT(*) FROM web_knowledge").fetchone()[0]

    conn.close()

    sources = []
    for row in web_stats:
        sources.append(
            {
                "name": row["site"],
                "type": "web",
                "page_count": row["page_count"],
                "last_crawled": row["last_crawled"],
            }
        )
    for row in social_stats:
        sources.append(
            {
                "name": row["platform"],
                "type": "social",
                "post_count": row["post_count"],
                "last_imported": row["last_imported"],
            }
        )

    return {"sources": sources, "knowledge_entries": knowledge_count}


# ------------------------------------------------------------------
# GET /stats — detailed knowledge breakdown
# ------------------------------------------------------------------


@router.get("/stats")
async def get_stats(db_path: str = Depends(get_db_path)):
    """Return detailed knowledge stats: by fact_type, by pillar, coverage gaps."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Total counts
    total_pages = conn.execute("SELECT COUNT(*) FROM web_pages").fetchone()[0]
    total_knowledge = conn.execute("SELECT COUNT(*) FROM web_knowledge").fetchone()[0]
    pages_with_knowledge = conn.execute(
        "SELECT COUNT(DISTINCT web_page_id) FROM web_knowledge WHERE web_page_id IS NOT NULL"
    ).fetchone()[0]
    pages_without = total_pages - pages_with_knowledge

    # By fact_type
    by_type = conn.execute(
        "SELECT fact_type, COUNT(*) as count FROM web_knowledge GROUP BY fact_type ORDER BY count DESC"
    ).fetchall()

    # By pillar
    by_pillar = conn.execute(
        """SELECT COALESCE(pillar, 'Unclassified') as pillar, COUNT(*) as count
           FROM web_knowledge GROUP BY pillar ORDER BY count DESC"""
    ).fetchall()

    # By topic
    by_topic = conn.execute(
        """SELECT COALESCE(topic, 'Unclassified') as topic, COUNT(*) as count
           FROM web_knowledge GROUP BY topic ORDER BY count DESC"""
    ).fetchall()

    # Coverage: pages with most/least knowledge
    coverage = conn.execute(
        """SELECT wp.title, wp.site, wp.url, COUNT(wk.id) as fact_count
           FROM web_pages wp
           LEFT JOIN web_knowledge wk ON wk.web_page_id = wp.id
           WHERE length(wp.body_text) > 200
           GROUP BY wp.id
           ORDER BY fact_count ASC
           LIMIT 10"""
    ).fetchall()

    conn.close()

    return {
        "total_pages": total_pages,
        "total_knowledge": total_knowledge,
        "pages_with_knowledge": pages_with_knowledge,
        "pages_without_knowledge": pages_without,
        "by_type": [{"type": r["fact_type"], "count": r["count"]} for r in by_type],
        "by_pillar": [{"pillar": r["pillar"], "count": r["count"]} for r in by_pillar],
        "by_topic": [{"topic": r["topic"], "count": r["count"]} for r in by_topic],
        "coverage_gaps": [
            {"title": r["title"], "site": r["site"], "url": r["url"], "fact_count": r["fact_count"]}
            for r in coverage
            if r["fact_count"] == 0
        ],
    }


# ------------------------------------------------------------------
# GET /graph — knowledge graph data (nodes + edges)
# ------------------------------------------------------------------


@router.get("/graph")
async def get_graph_data(db_path: str = Depends(get_db_path)):
    """Return nodes and links for force-directed knowledge graph."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    nodes = []
    links = []

    # Topic nodes (large) — primary grouping
    topics = conn.execute(
        """SELECT COALESCE(topic, 'Unclassified') as topic, COUNT(*) as count
           FROM web_knowledge GROUP BY topic"""
    ).fetchall()
    for t in topics:
        nodes.append(
            {
                "id": f"topic:{t['topic']}",
                "label": t["topic"],
                "type": "topic",
                "size": 8 + t["count"] // 3,
            }
        )

    # Page nodes (medium) — only pages with knowledge
    pages = conn.execute(
        """SELECT wp.id, wp.title, wp.site, COUNT(wk.id) as fact_count
           FROM web_pages wp
           JOIN web_knowledge wk ON wk.web_page_id = wp.id
           GROUP BY wp.id"""
    ).fetchall()
    for pg in pages:
        nodes.append(
            {
                "id": f"page:{pg['id']}",
                "label": pg["title"][:30],
                "type": "page",
                "site": pg["site"],
                "size": 3 + pg["fact_count"],
            }
        )

    # Fact nodes (small) + edges
    facts = conn.execute(
        """SELECT wk.id, wk.fact_type, wk.content, wk.topic, wk.web_page_id
           FROM web_knowledge wk LIMIT 200"""
    ).fetchall()
    for f in facts:
        fact_id = f"fact:{f['id']}"
        nodes.append({"id": fact_id, "label": f["content"][:40], "type": f["fact_type"], "size": 2})
        # Link fact → page
        if f["web_page_id"]:
            links.append({"source": f"page:{f['web_page_id']}", "target": fact_id})
        # Link fact → topic
        topic_key = f["topic"] or "Unclassified"
        links.append({"source": f"topic:{topic_key}", "target": fact_id})

    conn.close()
    return {"nodes": nodes, "links": links}


# ------------------------------------------------------------------
# GET /browse — paginated list of all knowledge entries
# ------------------------------------------------------------------


@router.get("/browse")
async def browse_knowledge(
    pillar: str | None = Query(default=None),
    topic: str | None = Query(default=None),
    fact_type: str | None = Query(default=None),
    site: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, le=200),
    db_path: str = Depends(get_db_path),
):
    """Browse all knowledge entries with filters and pagination."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    conditions = []
    params: list = []

    if pillar:
        conditions.append("wk.pillar = ?")
        params.append(pillar)
    if topic:
        if topic == "Unclassified":
            conditions.append("wk.topic IS NULL")
        else:
            conditions.append("wk.topic = ?")
            params.append(topic)
    if fact_type:
        conditions.append("wk.fact_type = ?")
        params.append(fact_type)
    if site:
        conditions.append("wp.site = ?")
        params.append(site)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    total = conn.execute(
        f"""SELECT COUNT(*) FROM web_knowledge wk
            LEFT JOIN web_pages wp ON wk.web_page_id = wp.id {where}""",
        params,
    ).fetchone()[0]

    offset = (page - 1) * per_page
    rows = conn.execute(
        f"""SELECT wk.id, wk.fact_type, wk.content, wk.topic, wk.pillar, wk.keywords,
                   wp.title as page_title, wp.url as page_url, wp.site
            FROM web_knowledge wk
            LEFT JOIN web_pages wp ON wk.web_page_id = wp.id
            {where}
            ORDER BY wk.id DESC
            LIMIT ? OFFSET ?""",
        [*params, per_page, offset],
    ).fetchall()

    conn.close()

    results = []
    for row in rows:
        keywords = []
        if row["keywords"]:
            try:
                keywords = json.loads(row["keywords"])
            except (json.JSONDecodeError, TypeError):
                pass
        results.append(
            {
                "id": row["id"],
                "fact_type": row["fact_type"],
                "content": row["content"],
                "topic": row["topic"],
                "pillar": row["pillar"],
                "keywords": keywords,
                "page_title": row["page_title"],
                "page_url": row["page_url"],
                "site": row["site"],
            }
        )

    return {
        "results": results,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }


# ------------------------------------------------------------------
# GET /search — full-text search across knowledge base
# ------------------------------------------------------------------


@router.get("/search")
async def search_knowledge(
    q: str = Query(default=""),
    pillar: str | None = Query(default=None),
    fact_type: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    db_path: str = Depends(get_db_path),
):
    """Search knowledge entries by text, pillar, or fact_type."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    conditions = []
    params: list = []

    if q:
        conditions.append("(wk.content LIKE ? OR wp.title LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%"])
    if pillar:
        conditions.append("wk.pillar = ?")
        params.append(pillar)
    if fact_type:
        conditions.append("wk.fact_type = ?")
        params.append(fact_type)

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    params.append(limit)

    rows = conn.execute(
        f"""SELECT wk.id, wk.fact_type, wk.content, wk.topic, wk.pillar, wk.keywords,
                   wp.title as page_title, wp.url as page_url, wp.site
            FROM web_knowledge wk
            LEFT JOIN web_pages wp ON wk.web_page_id = wp.id
            WHERE {where_clause}
            ORDER BY wk.id DESC
            LIMIT ?""",
        params,
    ).fetchall()

    conn.close()

    results = []
    for row in rows:
        keywords = []
        if row["keywords"]:
            try:
                keywords = json.loads(row["keywords"])
            except (json.JSONDecodeError, TypeError):
                pass
        results.append(
            {
                "id": row["id"],
                "fact_type": row["fact_type"],
                "content": row["content"],
                "topic": row["topic"],
                "pillar": row["pillar"],
                "keywords": keywords,
                "page_title": row["page_title"],
                "page_url": row["page_url"],
                "site": row["site"],
            }
        )

    return {"results": results, "count": len(results)}


# ------------------------------------------------------------------
# GET /progress — poll crawl progress
# ------------------------------------------------------------------


@router.get("/progress")
async def get_crawl_progress():
    """Return current crawl/import progress."""
    return _crawl_progress


# ------------------------------------------------------------------
# POST /crawl — trigger website re-crawl (background task)
# ------------------------------------------------------------------


@router.post("/crawl")
async def trigger_crawl(background_tasks: BackgroundTasks):
    """Trigger a re-crawl of configured websites. Runs in background."""
    if _crawl_progress["running"]:
        return {"status": "already_running", "message": "A crawl is already in progress"}
    background_tasks.add_task(_run_web_crawl)
    return {"status": "started", "message": "Web crawl started in background"}


def _is_content_unchanged(db_path: str, url: str, site: str, new_hash: str) -> bool:
    """Check if a page's content_hash matches what's already stored."""
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT content_hash FROM web_pages WHERE url = ? AND site = ?", (url, site)
    ).fetchone()
    conn.close()
    return row is not None and row[0] == new_hash


async def _run_web_crawl():
    """Background task: crawl gitavalley.org and iskcongitanagari.org."""
    global _crawl_progress
    from content_engine.crawlers.wordpress_crawler import WordPressCrawler
    from content_engine.pillars import get_active_pillar_names

    db_path = get_db_path()
    pillars = get_active_pillar_names()
    _crawl_progress = {"running": True, "source": "", "current": 0, "total": 0, "phase": "starting"}

    skipped = 0
    processed = 0
    try:
        # --- WordPress crawler (gitavalley.org) ---
        wp = WordPressCrawler()
        try:
            _crawl_progress.update(source="gitavalley.org", phase="fetching pages from API")
            pages = await wp.crawl_all()
            _crawl_progress["total"] = len(pages)

            for i, page in enumerate(pages):
                # Skip if content unchanged (SHA-256 match)
                if _is_content_unchanged(db_path, page["url"], page["site"], page["content_hash"]):
                    skipped += 1
                    _crawl_progress.update(
                        current=i + 1,
                        phase=f"skipped (unchanged): {page['title'][:30]}",
                    )
                    continue

                processed += 1
                _crawl_progress.update(
                    current=i + 1,
                    phase=f"extracting: {page['title'][:30]}",
                )

                try:
                    pillar = wp.classify_pillar(page["title"], page["body_text"], pillars)
                    page_id = wp.store_page_sync(db_path, page, pillar=pillar)
                    knowledge = wp.extract_knowledge(page["title"], page["body_text"])
                    if knowledge:
                        wp.store_knowledge_sync(db_path, page_id, knowledge, pillar=pillar)
                except Exception:
                    logger.exception("Error processing page %s", page["url"])
                    wp.store_page_sync(db_path, page, pillar=None)
        finally:
            await wp.close()

        # --- ISKCON Gita Nagari (also WordPress) ---
        iskcon = WordPressCrawler(
            base_url="https://www.iskcongitanagari.org",
            site_name="iskcon",
        )
        try:
            _crawl_progress.update(
                source="iskcongitanagari.org", phase="fetching pages from API", current=0, total=0
            )
            pages = await iskcon.crawl_all()
            _crawl_progress["total"] = len(pages)

            for i, page in enumerate(pages):
                if _is_content_unchanged(db_path, page["url"], page["site"], page["content_hash"]):
                    skipped += 1
                    _crawl_progress.update(
                        current=i + 1,
                        phase=f"skipped (unchanged): {page['title'][:30]}",
                    )
                    continue

                processed += 1
                _crawl_progress.update(current=i + 1, phase=f"extracting: {page['title'][:30]}")

                try:
                    pillar = iskcon.classify_pillar(page["title"], page["body_text"], pillars)
                    page_id = iskcon.store_page_sync(db_path, page, pillar=pillar)
                    knowledge = iskcon.extract_knowledge(page["title"], page["body_text"])
                    if knowledge:
                        iskcon.store_knowledge_sync(db_path, page_id, knowledge, pillar=pillar)
                except Exception:
                    logger.exception("Error processing ISKCON page %s", page["url"])
                    iskcon.store_page_sync(db_path, page, pillar=None)
        except Exception:
            logger.exception("ISKCON crawler failed")
        finally:
            await iskcon.close()

        logger.info("Crawl complete: %d processed, %d skipped (unchanged)", processed, skipped)
        _crawl_progress.update(
            phase=f"complete — {processed} updated, {skipped} unchanged", running=False
        )
    except Exception:
        logger.exception("Crawl task failed")
        _crawl_progress.update(phase="error", running=False)


# ------------------------------------------------------------------
# POST /import-social — trigger Meta Graph API import
# ------------------------------------------------------------------


@router.post("/import-social")
async def trigger_social_import(background_tasks: BackgroundTasks):
    """Trigger Meta Graph API import. Runs in background."""
    background_tasks.add_task(_run_social_import)
    return {"status": "started", "message": "Social import started in background"}


async def _run_social_import():
    """Background task: import posts from Facebook and Instagram."""
    import os

    from content_engine.crawlers.meta_importer import MetaGraphImporter

    token = os.getenv("META_PAGE_TOKEN", "")
    if not token:
        return

    db_path = get_db_path()
    importer = MetaGraphImporter(
        access_token=token,
        page_id=os.getenv("META_PAGE_ID", ""),
        instagram_account_id=os.getenv("META_INSTAGRAM_ACCOUNT_ID"),
    )
    try:
        posts = await importer.import_all()
        for post in posts:
            importer.store_post_sync(db_path, post)
    finally:
        await importer.close()
