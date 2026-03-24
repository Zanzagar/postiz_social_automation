"""System health check endpoints."""

import asyncio
import time
from datetime import UTC, datetime
from functools import partial

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

# OAuth check is slow (subprocess) and rarely changes — cache separately
_oauth_cache: dict = {"result": None, "expires": 0}
_OAUTH_CACHE_TTL = 300  # 5 minutes


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
        # Run all checks concurrently in thread pool to avoid blocking the event loop.
        # OAuth uses a longer cache since it rarely changes and is the slowest check.
        oauth_result = None
        if _oauth_cache["result"] and now < _oauth_cache["expires"]:
            oauth_result = _oauth_cache["result"]

        loop = asyncio.get_event_loop()
        checks_to_run = [
            ("sheets", partial(check_sheets_health, sheets)),
            ("postiz", partial(check_postiz_health, postiz)),
            ("claude", check_claude_health),
        ]
        if oauth_result is None:
            checks_to_run.append(("oauth", check_oauth_health))

        results = await asyncio.gather(*(loop.run_in_executor(None, fn) for _, fn in checks_to_run))

        for (name, _), (ok, msg) in zip(checks_to_run, results):
            if name == "oauth":
                _oauth_cache["result"] = (ok, msg)
                _oauth_cache["expires"] = time.time() + _OAUTH_CACHE_TTL
            services.append(
                ServiceHealth(
                    name=name,
                    status="ok" if ok else "error",
                    message=msg,
                    last_checked=checked_at,
                )
            )

        # Append cached OAuth if we didn't re-check it
        if oauth_result is not None:
            ok, msg = oauth_result
            services.append(
                ServiceHealth(
                    name="oauth",
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
