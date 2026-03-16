"""System health check endpoints."""

import time
from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from api.auth import get_current_user
from api.dependencies import get_postiz_client, get_settings, get_sheets_client
from api.schemas import HealthResponse, ServiceHealth
from content_engine.health import (
    check_claude_health,
    check_oauth_health,
    check_postiz_health,
    check_sheets_health,
)

router = APIRouter(prefix="/api", tags=["health"], dependencies=[Depends(get_current_user)])

# Simple cache for health checks
_health_cache: dict = {"data": None, "expires": 0}
_CACHE_TTL = 30  # seconds


@router.get("/health", response_model=HealthResponse)
async def system_health(
    sheets=Depends(get_sheets_client),
    postiz=Depends(get_postiz_client),
):
    """Check health of all external services."""
    now = time.time()
    if _health_cache["data"] and now < _health_cache["expires"]:
        return _health_cache["data"]

    checked_at = datetime.now(UTC)
    settings = get_settings()
    services = []

    if settings.demo_mode:
        for name, msg in [
            ("sheets", "Demo mode — Google Sheets connected"),
            ("postiz", "Demo mode — 2 integrations (IG, FB)"),
            ("claude", "Demo mode — Claude AI ready"),
            ("oauth", "Demo mode — OAuth token valid"),
        ]:
            services.append(
                ServiceHealth(name=name, status="ok", message=msg, last_checked=checked_at)
            )
    else:
        for name, check_fn, args in [
            ("sheets", check_sheets_health, (sheets,)),
            ("postiz", check_postiz_health, (postiz,)),
            ("claude", check_claude_health, ()),
            ("oauth", check_oauth_health, ()),
        ]:
            ok, msg = check_fn(*args)
            services.append(
                ServiceHealth(
                    name=name,
                    status="ok" if ok else "error",
                    message=msg,
                    last_checked=checked_at,
                )
            )

    # Fetch recent errors
    errors = []
    try:
        errors = sheets.get_recent_errors(limit=10)
    except Exception:
        pass

    response = HealthResponse(services=services, errors=errors)
    _health_cache["data"] = response
    _health_cache["expires"] = now + _CACHE_TTL
    return response
