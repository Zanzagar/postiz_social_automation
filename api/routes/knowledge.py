"""Knowledge base API endpoints — crawl triggers, status, search."""

import json
import sqlite3
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Query

from api.auth import get_current_user

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
# POST /crawl — trigger website re-crawl (background task)
# ------------------------------------------------------------------


@router.post("/crawl")
async def trigger_crawl(background_tasks: BackgroundTasks):
    """Trigger a re-crawl of configured websites. Runs in background."""
    background_tasks.add_task(_run_web_crawl)
    return {"status": "started", "message": "Web crawl started in background"}


async def _run_web_crawl():
    """Background task: crawl gitavalley.com and iskcongitanagari.org."""
    from content_engine.crawlers.web_scraper import WebScraper
    from content_engine.crawlers.wordpress_crawler import WordPressCrawler
    from content_engine.pillars import get_active_pillar_names

    db_path = get_db_path()
    pillars = get_active_pillar_names()

    # WordPress crawler
    wp = WordPressCrawler()
    try:
        pages = await wp.crawl_all()
        for page in pages:
            pillar = wp.classify_pillar(page["title"], page["body_text"], pillars)
            page_id = wp.store_page_sync(db_path, page, pillar=pillar)
            knowledge = wp.extract_knowledge(page["title"], page["body_text"])
            wp.store_knowledge_sync(db_path, page_id, knowledge, pillar=pillar)
    finally:
        await wp.close()

    # BeautifulSoup scraper
    scraper = WebScraper("https://iskcongitanagari.org", "iskcon")
    try:
        pages = await scraper.crawl_site()
        for page in pages:
            scraper.store_page_sync(db_path, page)
    except Exception:
        pass  # Error handling in Task 9


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
