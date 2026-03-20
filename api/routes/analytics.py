"""Analytics API endpoints — overview, pillar breakdown, top posts."""

from pathlib import Path

from fastapi import APIRouter, Depends, Query

from api.auth import get_current_user

router = APIRouter(
    prefix="/api/analytics", tags=["analytics"], dependencies=[Depends(get_current_user)]
)

_DEFAULT_DB_PATH = str(Path("data/gvsa.db"))


def get_db_path() -> str:
    """Return path to SQLite database. Patchable for tests."""
    return _DEFAULT_DB_PATH


@router.get("/overview")
async def get_overview(db_path: str = Depends(get_db_path)):
    """Return aggregate engagement overview."""
    from content_engine.analytics.correlation import AnalyticsEngine

    engine = AnalyticsEngine(db_path)
    return engine.get_overview()


@router.get("/pillars")
async def get_pillar_breakdown(db_path: str = Depends(get_db_path)):
    """Return engagement stats grouped by content pillar."""
    from content_engine.analytics.correlation import AnalyticsEngine

    engine = AnalyticsEngine(db_path)
    return {"pillars": engine.get_pillar_breakdown()}


@router.get("/top-posts")
async def get_top_posts(
    limit: int = Query(default=10, le=50),
    db_path: str = Depends(get_db_path),
):
    """Return top posts by engagement."""
    from content_engine.analytics.correlation import AnalyticsEngine

    engine = AnalyticsEngine(db_path)
    return {"posts": engine.get_top_posts(limit=limit)}
