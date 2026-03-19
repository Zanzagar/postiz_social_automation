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
        f"""SELECT wk.id, wk.fact_type, wk.content, wk.pillar, wk.keywords,
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
    from content_engine.crawlers.web_scraper import WebScraper
    from content_engine.crawlers.wordpress_crawler import WordPressCrawler
    from content_engine.pillars import get_active_pillar_names

    db_path = get_db_path()
    pillars = get_active_pillar_names()
    _crawl_progress = {"running": True, "source": "", "current": 0, "total": 0, "phase": "starting"}

    try:
        # --- WordPress crawler (gitavalley.org) ---
        wp = WordPressCrawler()
        try:
            _crawl_progress.update(source="gitavalley.org", phase="fetching pages")
            pages = await wp.crawl_all()
            _crawl_progress["total"] = len(pages)

            for i, page in enumerate(pages):
                _crawl_progress.update(current=i + 1, phase=f"processing: {page['title'][:30]}")

                # Skip if content unchanged
                if _is_content_unchanged(db_path, page["url"], page["site"], page["content_hash"]):
                    continue

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

        # --- BeautifulSoup scraper (iskcongitanagari.org) ---
        scraper = WebScraper("https://iskcongitanagari.org", "iskcon")
        try:
            _crawl_progress.update(
                source="iskcongitanagari.org", phase="crawling site", current=0, total=0
            )
            pages = await scraper.crawl_site()
            _crawl_progress["total"] = len(pages)

            for i, page in enumerate(pages):
                _crawl_progress.update(current=i + 1, phase=f"processing: {page['title'][:30]}")

                if _is_content_unchanged(db_path, page["url"], page["site"], page["content_hash"]):
                    continue

                try:
                    scraper.store_page_sync(db_path, page)
                    # Extract knowledge using WordPress crawler's Claude methods
                    if page["body_text"] and len(page["body_text"]) > 100:
                        knowledge = wp.extract_knowledge(page["title"], page["body_text"])
                        if knowledge:
                            conn = sqlite3.connect(db_path)
                            pid = conn.execute(
                                "SELECT id FROM web_pages WHERE url = ? AND site = ?",
                                (page["url"], page["site"]),
                            ).fetchone()
                            conn.close()
                            if pid:
                                wp.store_knowledge_sync(db_path, pid[0], knowledge)
                except Exception:
                    logger.exception("Error processing ISKCON page %s", page["url"])
        except Exception:
            logger.exception("ISKCON scraper failed")

        _crawl_progress.update(phase="complete", running=False)
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
