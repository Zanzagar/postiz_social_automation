"""Auto-publish eligibility rule and release loop (Phase 1).

Single source of truth for the auto-publish semantics defined in
POSTIZ_CONTRACT.md §7 (G6): on approve, a row gets an auto_publish_at
timestamp if eligible; a background loop releases due rows as one Postiz
post per platform.

Datetime invariant
------------------
All datetimes written to ContentRow (auto_publish_at, held_at, posted_at)
are produced from ``datetime.now(UTC)``. SQLite's DateTime column strips
the tzinfo on write and returns naive values on read, so **naive datetimes
loaded from the DB are always UTC wall-clock time**. Every reader must
normalize with :func:`_as_utc` (attach UTC, never convert) and every
writer must use aware-UTC "now" values so the stored wall time is UTC.
Staff-entered ``row.date`` values follow the same convention.
"""

import asyncio
import json
import logging
import re
from collections import deque
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import ContentRow, PublishConfig
from api.schemas import PlatformPublishResult
from api.services.media_public import resolve_public_media_url

logger = logging.getLogger(__name__)

BUDGET_EXHAUSTED_MESSAGE = "Postiz hourly request budget exhausted — try again in a few minutes"

# Cap rows examined per 30s cycle so one backlog burst can't starve others.
MAX_ROWS_PER_CYCLE = 5
LOOP_INTERVAL_SECONDS = 30.0

# Postiz allows 30 requests/hour TOTAL. Budget publish requests (one per
# platform publish) against a rolling one-hour window, keeping headroom for
# list_integrations calls and interactive use of the API.
#
# NOTE: this module-level window only works for the current single-process
# deploy. A multi-worker deploy needs a real distributed lock / row-claim
# mechanism plus shared rate accounting (out of scope for Phase 1).
REQUEST_BUDGET_PER_HOUR = 20
_request_times: deque[datetime] = deque()

# --- In-process row claim (double-publish guard) ---
#
# Without coordination, the release loop and POST /content/{id}/publish-now
# (or two concurrent publish-now calls) can each read the same row's pending
# platforms before either commits, and both publish them (double-post). A
# publisher must claim the row id here BEFORE reading pending platforms and
# release it AFTER its commit. Like the request budget above, this
# in-process claim is correct only for the current single-process deploy
# (documented assumption); a multi-worker deploy needs a real distributed
# lock / row-claim mechanism.
_in_flight_rows: set[int] = set()
_claim_lock = asyncio.Lock()


async def acquire_row_claim(row_id: int) -> bool:
    """Try to claim a row for publishing. False when already in flight."""
    async with _claim_lock:
        if row_id in _in_flight_rows:
            return False
        _in_flight_rows.add(row_id)
        return True


async def release_row_claim(row_id: int) -> None:
    """Release a row claim (safe to call for ids that are not claimed)."""
    async with _claim_lock:
        _in_flight_rows.discard(row_id)


def _budget_remaining(now: datetime, budget: int = REQUEST_BUDGET_PER_HOUR) -> int:
    """Requests still available in the rolling one-hour window ending at now."""
    cutoff = now - timedelta(hours=1)
    while _request_times and _request_times[0] <= cutoff:
        _request_times.popleft()
    return budget - len(_request_times)


def _record_request(now: datetime) -> None:
    _request_times.append(now)


def publish_budget_remaining(now: datetime, budget: int = REQUEST_BUDGET_PER_HOUR) -> int:
    """Public read of the rolling publish-request budget (endpoints use this
    to fail fast with 429 instead of starting a doomed publish)."""
    return _budget_remaining(now, budget)


# Failure notes written by the release core, e.g.
# "[auto-publish 2026-07-06T12:00:00+00:00] failed for instagram: boom; row held"
_FAILED_NOTE_RE = re.compile(r"^\[auto-publish [^\]]*\] failed for (.+?)(?:; row held)?$")


def parse_last_publish_failure(feedback: str | None) -> str | None:
    """Extract the human part of the LAST publish-failure note in feedback.

    Returns e.g. "instagram: boom" (the text after "failed for ", without
    the mechanical "; row held" suffix), or None when no failure note
    exists. Used to populate ContentRowResponse.error_msg.
    """
    if not feedback:
        return None
    last: str | None = None
    for line in feedback.splitlines():
        match = _FAILED_NOTE_RE.match(line.strip())
        if match:
            last = match.group(1).strip()
    return last or None


def _parse_json_dict(value: str | None) -> dict:
    """Parse a JSON-as-TEXT column, returning {} on None/invalid."""
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _has_media(row: ContentRow) -> bool:
    """True if the row has any attached media (URL or catalog items)."""
    if row.media_url:
        return True
    if row.media_catalog_ids:
        try:
            ids = json.loads(row.media_catalog_ids)
            return bool(ids)
        except (json.JSONDecodeError, TypeError):
            # Unparseable but non-empty — treat conservatively as media
            return True
    return False


def no_alt_block(row: ContentRow) -> bool:
    """NO-ALT block: row has media but no alt text.

    Blocks scheduling/auto-release for publishing purposes. Saving drafts
    is always allowed.
    """
    return _has_media(row) and not (row.alt_text and row.alt_text.strip())


def _pillar_allowed(config: PublishConfig, pillar: str | None) -> bool:
    """Check a platform config's pillar_overrides map for the row's pillar.

    A pillar mapped to False (or "hold") means always hold; missing means
    allowed.
    """
    if pillar is None:
        return True
    overrides = _parse_json_dict(config.pillar_overrides)
    value = overrides.get(pillar, True)
    return not (value is False or value == "hold")


def _platform_auto_eligible(config: PublishConfig | None, pillar: str | None) -> bool:
    """A platform may auto-release only if its config is enabled and the
    row's pillar is not held by that config."""
    return config is not None and bool(config.enabled) and _pillar_allowed(config, pillar)


def compute_auto_publish_at(
    row: ContentRow,
    configs: list[PublishConfig],
    now: datetime,
) -> datetime | None:
    """Eligibility rule: return now + delay_hours if the row may auto-release.

    Eligible IF:
    - at least one of the row's enabled platforms has PublishConfig.enabled
      AND that config does not except the row's pillar, AND
    - row.require_review is false, AND
    - no NO-ALT block.

    Uses the minimum delay among qualifying platform configs. Returns None
    (manual release) when ineligible.
    """
    if row.require_review:
        return None
    if no_alt_block(row):
        return None

    platforms = _parse_json_dict(row.platforms)
    enabled_platforms = [p for p, on in platforms.items() if on]
    if not enabled_platforms:
        return None

    by_platform = {c.platform: c for c in configs}
    delays = [
        by_platform[p].delay_hours
        for p in enabled_platforms
        if _platform_auto_eligible(by_platform.get(p), row.pillar)
    ]
    if not delays:
        return None
    return now + timedelta(hours=min(delays))


def _as_utc(dt: datetime | None) -> datetime | None:
    """Normalize a possibly-naive DB datetime to aware UTC.

    Per the module-level datetime invariant, naive values loaded from the
    DB are UTC wall-clock time (they were written from datetime.now(UTC)
    and SQLite stripped the tzinfo), so we attach UTC without converting.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


async def release_row_platforms(
    session,
    row: ContentRow,
    platforms_to_publish: list[str],
    now: datetime,
    postiz,
    platform_map: dict[str, str],
    request_budget: int = REQUEST_BUDGET_PER_HOUR,
    *,
    manual: bool,
) -> tuple[list[PlatformPublishResult], str]:
    """Shared per-platform publish core for the release loop AND publish-now.

    Publishes one Postiz post per platform in ``platforms_to_publish``
    (callers pre-filter: the loop passes only auto-eligible pending
    platforms; manual passes ALL pending platforms). Applies the same row
    mutations in both modes: successful ids merged into row.postiz_ids,
    held_at + feedback note on failure, status/posted_at on full success.

    Mode differences:
    - manual=False (loop): stop at the first failure (byte-identical to the
      historical loop behavior); budget exhaustion defers silently.
    - manual=True: attempt every platform so the caller can report a
      per-platform result; budget exhaustion mid-row marks the remaining
      platforms failed with the budget message but does NOT hold the row.

    Returns (results, outcome) with outcome in "published" | "held" |
    "deferred".
    """
    captions = _parse_json_dict(row.captions)
    postiz_ids = _parse_json_dict(row.postiz_ids)

    # Schedule at the row's planned date when it is still in the future,
    # otherwise publish immediately.
    row_date = _as_utc(row.date)
    scheduled_at = row_date.isoformat() if row_date and row_date > now else None
    success_status = "scheduled" if scheduled_at else "posted"

    results: list[PlatformPublishResult] = []
    failures: list[str] = []  # real failures only — these hold the row
    deferred = False
    media_resolved = False
    media_url: str | None = None
    media_error: str | None = None

    def fail(platform: str, error: str, *, holds_row: bool = True) -> None:
        results.append(PlatformPublishResult(platform=platform, status="failed", error=error))
        if holds_row:
            failures.append(f"{platform}: {error}")

    for platform in platforms_to_publish:
        caption = captions.get(platform)
        integration_id = platform_map.get(platform)
        if not caption or not integration_id:
            fail(platform, f"missing {'caption' if not caption else 'Postiz integration'}")
            if not manual:
                break
            continue
        if deferred or _budget_remaining(now, request_budget) <= 0:
            deferred = True
            if not manual:
                break
            fail(platform, BUDGET_EXHAUSTED_MESSAGE, holds_row=False)
            continue
        if not media_resolved:
            # Resolve once per row; every platform shares the same media.
            media_resolved = True
            try:
                media_url = await resolve_public_media_url(session, row)
            except Exception as e:  # MediaNotPublicError or Drive error
                media_error = str(e)
        if media_error is not None:
            fail(platform, media_error)
            if not manual:
                break
            continue
        _record_request(now)
        try:
            result = await asyncio.to_thread(
                postiz.publish_post,
                caption,
                [integration_id],
                media_url,
                scheduled_at,
            )
            postiz_id = result.get("id", "")
            link = result.get("releaseURL") or None  # never fabricated
        except Exception as e:  # PostizAPIError or transport error
            fail(platform, str(e))
            if not manual:
                break
            continue
        postiz_ids[platform] = postiz_id
        results.append(
            PlatformPublishResult(
                platform=platform, status=success_status, postiz_id=postiz_id, link=link
            )
        )

    row.postiz_ids = json.dumps(postiz_ids) if postiz_ids else row.postiz_ids

    if failures:
        # Partial failure: hold the row so remaining platforms don't retry
        # blindly; a human resumes after fixing the cause.
        row.held_at = now
        failure = "; ".join(failures)
        note = f"[auto-publish {now.isoformat()}] failed for {failure}; row held"
        row.feedback = f"{row.feedback}\n{note}" if row.feedback else note
        logger.warning("Auto-publish partial failure on row %d: %s", row.id, failure)
        return results, "held"

    if deferred:
        # Budget exhausted: leave status/auto_publish_at untouched; published
        # platforms are recorded in postiz_ids so the next cycle resumes.
        logger.info(
            "Auto-publish row %d: hourly request budget exhausted; deferring to next cycle",
            row.id,
        )
        return results, "deferred"

    if scheduled_at:
        row.status = "scheduled"
    else:
        row.status = "posted"
        row.posted_at = now
    return results, "published"


async def _release_row(
    session,
    row: ContentRow,
    now: datetime,
    postiz,
    platform_map: dict[str, str],
    configs_by_platform: dict[str, PublishConfig],
    request_budget: int,
) -> str:
    """Publish one Postiz post per auto-eligible pending platform of a due row.

    Only platforms whose PublishConfig is enabled AND whose pillar is not
    held may auto-release; ineligible platforms are skipped silently and
    stay pending for manual release (they are never a failure).

    Returns an outcome string:
    - "published": all auto-eligible platforms published (row posted/scheduled)
    - "held": a real publish error on an eligible platform held the row
    - "deferred": hourly request budget exhausted mid-row; retry next cycle
    - "skipped": no auto-eligible platforms; row returned to manual release
    """
    platforms = _parse_json_dict(row.platforms)
    postiz_ids = _parse_json_dict(row.postiz_ids)

    enabled = [p for p, on in platforms.items() if on]
    pending = [p for p in enabled if p not in postiz_ids]

    eligible = [
        p for p in pending if _platform_auto_eligible(configs_by_platform.get(p), row.pillar)
    ]
    ineligible = [p for p in pending if p not in eligible]
    if ineligible:
        logger.info(
            "Auto-publish row %d: platforms %s not auto-eligible; leaving for manual release",
            row.id,
            ineligible,
        )

    if not eligible:
        # Nothing may auto-release: return the row to manual release so the
        # loop does not re-select it every cycle.
        row.auto_publish_at = None
        note = (
            f"[auto-publish {now.isoformat()}] no auto-eligible platforms; left for manual release"
        )
        row.feedback = f"{row.feedback}\n{note}" if row.feedback else note
        return "skipped"

    _, outcome = await release_row_platforms(
        session, row, eligible, now, postiz, platform_map, request_budget, manual=False
    )
    return outcome


async def release_due_rows(
    session: AsyncSession,
    now: datetime,
    postiz,
    max_rows: int = MAX_ROWS_PER_CYCLE,
    request_budget: int = REQUEST_BUDGET_PER_HOUR,
) -> dict:
    """One release-loop cycle: publish rows whose auto_publish_at has passed.

    Selects rows with status=='approved', auto_publish_at <= now and
    held_at IS NULL. Work is bounded two ways: max_rows per cycle, and a
    rolling one-hour request budget (Postiz allows 30 req/hour total).

    Each row is committed immediately after its outcome is recorded so a
    crash mid-cycle can never lose a published row's postiz_ids/status
    (which would double-post on the next cycle).

    Returns a summary dict:
    {"published": n, "held": n, "deferred": n, "skipped": n}.
    """
    result = await session.execute(
        select(ContentRow)
        .where(
            ContentRow.status == "approved",
            ContentRow.held_at.is_(None),
            ContentRow.auto_publish_at.isnot(None),
            ContentRow.auto_publish_at <= now,
        )
        .order_by(ContentRow.auto_publish_at)
    )
    due = list(result.scalars().all())

    deferred = max(0, len(due) - max_rows)
    summary = {"published": 0, "held": 0, "deferred": deferred, "skipped": 0}
    if not due:
        return summary
    if deferred:
        logger.info(
            "Auto-publish: %d rows due, deferring %d to next cycle (cap %d, Postiz rate limit)",
            len(due),
            deferred,
            max_rows,
        )

    try:
        integrations = await asyncio.to_thread(postiz.list_integrations)
    except Exception:
        logger.warning("Auto-publish: could not list Postiz integrations; skipping cycle")
        return summary
    platform_map = {i.get("identifier", "").lower(): i["id"] for i in integrations}

    cfg_result = await session.execute(select(PublishConfig))
    configs_by_platform = {c.platform: c for c in cfg_result.scalars().all()}

    batch = due[:max_rows]
    for idx, row in enumerate(batch):
        if _budget_remaining(now, request_budget) <= 0:
            remaining = len(batch) - idx
            summary["deferred"] += remaining
            logger.info(
                "Auto-publish: hourly request budget exhausted; deferring %d due rows",
                remaining,
            )
            break
        if not await acquire_row_claim(row.id):
            # Row is mid-publish elsewhere (publish-now); skip it rather
            # than race to a double-post — it is reconsidered next cycle.
            summary["deferred"] += 1
            logger.info(
                "Auto-publish row %d: already being published elsewhere; skipping this cycle",
                row.id,
            )
            continue
        try:
            outcome = await _release_row(
                session, row, now, postiz, platform_map, configs_by_platform, request_budget
            )
            summary[outcome] += 1
            # Commit per row: a crash later in the batch must not lose this
            # row's postiz_ids/status (re-publishing it would double-post).
            await session.commit()
        finally:
            # Claim is released on every exit path, including exceptions.
            await release_row_claim(row.id)

    return summary


def _close_client(postiz) -> None:
    """Best-effort close of a Postiz client's HTTP session."""
    close = getattr(postiz, "close", None)
    if callable(close):
        try:
            close()
        except Exception:
            logger.debug("Auto-publish: error closing Postiz client", exc_info=True)


async def auto_publish_worker(
    session_factory,
    postiz_factory,
    interval: float = LOOP_INTERVAL_SECONDS,
) -> None:
    """Thin asyncio wrapper: run release_due_rows forever every `interval`s.

    One PostizClient is reused across cycles (a client per cycle leaks HTTP
    sessions); it is closed and recreated after any cycle error.
    """
    logger.info("Auto-publish release loop started (interval %.0fs)", interval)
    postiz = None
    try:
        while True:
            try:
                if postiz is None:
                    postiz = postiz_factory()
                async with session_factory() as session:
                    await release_due_rows(session, datetime.now(UTC), postiz)
            except asyncio.CancelledError:
                logger.info("Auto-publish release loop stopped")
                raise
            except Exception:
                logger.exception("Auto-publish cycle failed")
                # Recreate the client next cycle in case its session is bad.
                if postiz is not None:
                    _close_client(postiz)
                    postiz = None
            await asyncio.sleep(interval)
    finally:
        if postiz is not None:
            _close_client(postiz)
