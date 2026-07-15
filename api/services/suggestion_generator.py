"""Suggestion generators: festival reminders, pillar gaps, template reminders.

Each generator returns candidate dicts keyed for upsert by ``source_key``.
``refresh_suggestions`` upserts candidates into the suggestions table without
ever resurrecting rows the user has dismissed or drafted.

All generators take an injectable ``today`` so tests can freeze the clock.
"""

import json
import logging
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import ContentRow, Pillar, SocialHistory, Suggestion, Template

logger = logging.getLogger(__name__)

CALENDAR_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "iskcon_calendar.json"

FESTIVAL_LOOKAHEAD_DAYS = 45
PILLAR_WINDOW_DAYS = 30
PILLAR_GAP_THRESHOLD_PCT = 5.0
COUNTED_STATUSES = ("posted", "scheduled")


def _iso_week_key(today: date) -> str:
    """Return the ISO year-week designator, e.g. '2026-W31'."""
    iso = today.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def generate_festival_suggestions(today: date, calendar_path: Path | None = None) -> list[dict]:
    """Suggest posts for festivals within the next FESTIVAL_LOOKAHEAD_DAYS days."""
    path = calendar_path or CALENDAR_PATH
    if not path.exists():
        return []
    try:
        festivals = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        logger.warning("Could not read festival calendar at %s", path)
        return []

    horizon = today + timedelta(days=FESTIVAL_LOOKAHEAD_DAYS)
    candidates: list[dict] = []
    for fest in festivals:
        try:
            fest_date = date.fromisoformat(fest["date"])
            name = fest["name"]
        except (KeyError, TypeError, ValueError):
            continue
        if not (today <= fest_date <= horizon):
            continue
        note = str(fest.get("significance", "")).strip()
        angles = fest.get("suggested_content_angles") or []
        if angles:
            note = f"{note} Idea: {angles[0]}" if note else f"Idea: {angles[0]}"
        candidates.append(
            {
                "type": "festival",
                "title": name,
                "note": note,
                "pillar": fest.get("content_pillar"),
                "suggested_date": fest_date,
                "source_key": f"festival:{name}:{fest['date']}",
            }
        )
    return candidates


async def generate_pillar_gap_suggestions(session: AsyncSession, today: date) -> list[dict]:
    """Flag active pillars whose last-30d post share is >5pp under target.

    Actual share combines content_rows (posted/scheduled) and social_history
    posts dated within the window. Date filtering happens in Python because
    stored datetimes mix naive and timezone-aware values.
    """
    result = await session.execute(
        select(Pillar).where(Pillar.is_active == True)  # noqa: E712
    )
    pillars = [p for p in result.scalars().all() if p.target_distribution is not None]
    if not pillars:
        return []

    window_start = today - timedelta(days=PILLAR_WINDOW_DAYS)

    rows_result = await session.execute(
        select(ContentRow.pillar, ContentRow.date).where(
            ContentRow.status.in_(COUNTED_STATUSES), ContentRow.date.isnot(None)
        )
    )
    history_result = await session.execute(
        select(SocialHistory.pillar, SocialHistory.posted_at).where(
            SocialHistory.posted_at.isnot(None)
        )
    )
    posts = [(pillar, dt.date()) for pillar, dt in rows_result.all()]
    posts += [(pillar, dt.date()) for pillar, dt in history_result.all()]

    in_window = [(pillar, d) for pillar, d in posts if window_start <= d <= today]
    total = len(in_window)

    counts: dict[str, int] = {}
    last_post: dict[str, date] = {}
    for pillar_name, post_date in in_window:
        if pillar_name:
            counts[pillar_name] = counts.get(pillar_name, 0) + 1
    for pillar_name, post_date in posts:
        if pillar_name and post_date <= today:
            existing = last_post.get(pillar_name)
            if existing is None or post_date > existing:
                last_post[pillar_name] = post_date

    week_key = _iso_week_key(today)
    candidates: list[dict] = []
    for pillar in pillars:
        target_pct = pillar.target_distribution * 100
        actual_pct = (counts.get(pillar.name, 0) / total * 100) if total else 0.0
        if target_pct - actual_pct <= PILLAR_GAP_THRESHOLD_PCT:
            continue
        last = last_post.get(pillar.name)
        if last is not None:
            days_since = (today - last).days
            recency = f"Last post in this pillar was {days_since} days ago."
        else:
            recency = "No posts recorded in this pillar yet."
        note = (
            f"Only {actual_pct:.0f}% of the last {PILLAR_WINDOW_DAYS} days' posts "
            f"vs a {target_pct:.0f}% target. {recency}"
        )
        candidates.append(
            {
                "type": "pillar_gap",
                "title": f"«{pillar.name}» has been quiet",
                "note": note,
                "pillar": pillar.name,
                "suggested_date": None,
                "source_key": f"pillar:{pillar.name}:{week_key}",
            }
        )
    return candidates


async def generate_template_suggestions(session: AsyncSession, today: date) -> list[dict]:
    """Weekly reminders for templates that carry a schedule_pattern."""
    result = await session.execute(select(Template).where(Template.schedule_pattern.isnot(None)))
    week_key = _iso_week_key(today)
    candidates: list[dict] = []
    for template in result.scalars().all():
        if not template.schedule_pattern:
            continue
        candidates.append(
            {
                "type": "template",
                "title": f"Scheduled template: {template.name}",
                "note": (
                    f"Template '{template.name}' runs on schedule "
                    f"'{template.schedule_pattern}' — create this week's drafts."
                ),
                "pillar": template.pillar,
                "suggested_date": None,
                "source_key": f"template:{template.id}:{week_key}",
            }
        )
    return candidates


async def refresh_suggestions(
    session: AsyncSession,
    today: date | None = None,
    calendar_path: Path | None = None,
) -> None:
    """Run all generators and upsert candidates by source_key.

    Rows whose status is "dismissed" or "drafted" are never resurrected —
    the upsert only inserts new rows or updates rows still in "suggested".
    """
    today = today or date.today()
    candidates = generate_festival_suggestions(today, calendar_path)
    candidates += await generate_pillar_gap_suggestions(session, today)
    candidates += await generate_template_suggestions(session, today)

    for cand in candidates:
        result = await session.execute(
            select(Suggestion).where(Suggestion.source_key == cand["source_key"])
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            session.add(Suggestion(status="suggested", **cand))
        elif existing.status == "suggested":
            existing.type = cand["type"]
            existing.title = cand["title"]
            existing.note = cand["note"]
            existing.pillar = cand["pillar"]
            existing.suggested_date = cand["suggested_date"]
            existing.updated_at = datetime.now(UTC)
        # dismissed/drafted rows: leave untouched
    await session.commit()
