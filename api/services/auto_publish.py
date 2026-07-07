"""Auto-publish eligibility rule and release loop (Phase 1).

Single source of truth for the auto-publish semantics defined in
POSTIZ_CONTRACT.md §7 (G6): on approve, a row gets an auto_publish_at
timestamp if eligible; a background loop releases due rows as one Postiz
post per platform.
"""

import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import ContentRow, PublishConfig

logger = logging.getLogger(__name__)

# Postiz rate limit is 30 req/hour — cap work per 30s cycle so a backlog
# never bursts through the limit.
MAX_ROWS_PER_CYCLE = 5
LOOP_INTERVAL_SECONDS = 30.0


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
        if p in by_platform
        and by_platform[p].enabled
        and _pillar_allowed(by_platform[p], row.pillar)
    ]
    if not delays:
        return None
    return now + timedelta(hours=min(delays))


def _as_utc(dt: datetime | None) -> datetime | None:
    """Normalize a possibly-naive DB datetime to aware UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


async def _release_row(
    session: AsyncSession,
    row: ContentRow,
    now: datetime,
    postiz,
    platform_map: dict[str, str],
) -> bool:
    """Publish one Postiz post per enabled platform for a due row.

    Returns True if all platforms published; False if the row was held
    due to a partial failure.
    """
    platforms = _parse_json_dict(row.platforms)
    captions = _parse_json_dict(row.captions)
    postiz_ids = _parse_json_dict(row.postiz_ids)

    enabled = [p for p, on in platforms.items() if on]
    pending = [p for p in enabled if p not in postiz_ids]

    # Schedule at the row's planned date when it is still in the future,
    # otherwise publish immediately.
    row_date = _as_utc(row.date)
    scheduled_at = row_date.isoformat() if row_date and row_date > now else None

    failure: str | None = None
    for platform in pending:
        caption = captions.get(platform)
        integration_id = platform_map.get(platform)
        if not caption or not integration_id:
            failure = f"{platform}: missing {'caption' if not caption else 'Postiz integration'}"
            break
        try:
            result = await asyncio.to_thread(
                postiz.publish_post,
                caption,
                [integration_id],
                row.media_url,
                scheduled_at,
            )
            postiz_ids[platform] = result.get("id", "")
        except Exception as e:  # PostizAPIError or transport error
            failure = f"{platform}: {e}"
            break

    row.postiz_ids = json.dumps(postiz_ids) if postiz_ids else row.postiz_ids

    if failure is not None:
        # Partial failure: hold the row so remaining platforms don't retry
        # blindly; a human resumes after fixing the cause.
        row.held_at = now
        note = f"[auto-publish {now.isoformat()}] failed for {failure}; row held"
        row.feedback = f"{row.feedback}\n{note}" if row.feedback else note
        logger.warning("Auto-publish partial failure on row %d: %s", row.id, failure)
        return False

    if scheduled_at:
        row.status = "scheduled"
    else:
        row.status = "posted"
        row.posted_at = now
    return True


async def release_due_rows(
    session: AsyncSession,
    now: datetime,
    postiz,
    max_rows: int = MAX_ROWS_PER_CYCLE,
) -> dict:
    """One release-loop cycle: publish rows whose auto_publish_at has passed.

    Selects rows with status=='approved', auto_publish_at <= now and
    held_at IS NULL. Caps work at max_rows per cycle (Postiz 30 req/h).

    Returns a summary dict: {"published": n, "held": n, "deferred": n}.
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
    summary = {"published": 0, "held": 0, "deferred": deferred}
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

    for row in due[:max_rows]:
        ok = await _release_row(session, row, now, postiz, platform_map)
        summary["published" if ok else "held"] += 1

    await session.commit()
    return summary


async def auto_publish_worker(
    session_factory,
    postiz_factory,
    interval: float = LOOP_INTERVAL_SECONDS,
) -> None:
    """Thin asyncio wrapper: run release_due_rows forever every `interval`s."""
    logger.info("Auto-publish release loop started (interval %.0fs)", interval)
    while True:
        try:
            async with session_factory() as session:
                postiz = postiz_factory()
                await release_due_rows(session, datetime.now(UTC), postiz)
        except asyncio.CancelledError:
            logger.info("Auto-publish release loop stopped")
            raise
        except Exception:
            logger.exception("Auto-publish cycle failed")
        await asyncio.sleep(interval)
