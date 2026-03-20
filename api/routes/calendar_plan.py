"""AI calendar planning endpoints — generate content calendars using Claude."""

import json
import logging
import subprocess
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from api.dependencies import get_db
from api.models import CalendarPlan, MediaCatalog, Pillar, WebKnowledge
from api.routes.festivals import _load_festivals
from api.schemas import CalendarPlanCreate, CalendarPlanResponse, CalendarPlanSlot

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/calendar",
    tags=["calendar-plan"],
    dependencies=[Depends(get_current_user)],
)


def _run_claude(prompt: str) -> str:
    """Run Claude CLI with a prompt and return the response text."""
    result = subprocess.run(
        ["claude", "-p", prompt],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Claude CLI failed: {result.stderr[:200]}")
    return result.stdout.strip()


def _festivals_in_range(start: str, end: str) -> list[dict]:
    """Load ISKCON festivals falling within the date range."""
    festivals = _load_festivals()
    results = []
    for f in festivals:
        if start <= f["date"] <= end:
            results.append(f)
    return results


def _build_prompt(
    start: str,
    end: str,
    platforms: list[str],
    pillars: list[dict],
    festivals: list[dict],
    knowledge: list[dict],
    top_media: list[dict],
    constraints: str | None,
) -> str:
    """Build the Claude prompt for calendar generation."""
    pillar_lines = "\n".join(
        f"- {p['name']}: {int(p['weight'] * 100)}% target" for p in pillars if p["weight"]
    )

    festival_lines = (
        "\n".join(f"- {f['name']} ({f['date']}): {f['significance'][:100]}" for f in festivals)
        or "None in this period"
    )

    knowledge_lines = (
        "\n".join(f"- [{k['pillar']}] {k['content'][:120]}" for k in knowledge[:20])
        or "No knowledge base entries"
    )

    media_lines = (
        "\n".join(
            f"- ID {m['id']}: {m['filename']} (engagement: {m['engagement']:.2f})"
            for m in top_media[:10]
        )
        or "No media available"
    )

    constraint_block = ""
    if constraints:
        constraint_block = f"\nAdditional constraints:\n{constraints}\n"

    prompt = f"""Generate a content calendar for Gita Valley \
(ISKCON Gita Nagari) from {start} to {end}.
Target platforms: {", ".join(platforms)}

Pillar distribution targets:
{pillar_lines}

Upcoming festivals:
{festival_lines}

Knowledge base entries for content ideas:
{knowledge_lines}

High-performing media available:
{media_lines}
{constraint_block}
For each post slot provide a JSON array of objects with these fields:
- date (YYYY-MM-DD)
- time (HH:MM, optimal posting time)
- pillar (must follow distribution targets above)
- topic (specific topic within the pillar)
- content_idea (specific, actionable idea — 1-2 sentences)
- recommended_media_id (integer ID from the media list above, or null)
- target_platforms (array of platform names)

Aim for 1-2 posts per day. Prioritize festival days with related content.

Return ONLY the JSON array, no markdown fences or explanation."""

    return prompt


@router.post("/plan", status_code=201)
async def create_calendar_plan(
    req: CalendarPlanCreate,
    session: AsyncSession = Depends(get_db),
):
    """Generate an AI content calendar plan using Claude."""
    # Validate date range
    if req.date_range_start >= req.date_range_end:
        raise HTTPException(
            status_code=400,
            detail="date_range_start must be before date_range_end",
        )

    # Gather data for prompt
    # 1. Pillars with distribution weights
    pillar_result = await session.execute(select(Pillar).where(Pillar.is_active.is_(True)))
    pillars = [
        {"name": p.name, "weight": p.target_distribution or 0.0}
        for p in pillar_result.scalars().all()
    ]

    # 2. Festivals in range
    festivals = _festivals_in_range(req.date_range_start, req.date_range_end)

    # 3. Knowledge base entries (sample for prompt context)
    knowledge_result = await session.execute(select(WebKnowledge).limit(20))
    knowledge = [
        {"pillar": k.pillar or "", "content": k.content} for k in knowledge_result.scalars().all()
    ]

    # 4. Top media by engagement
    media_result = await session.execute(
        select(MediaCatalog).order_by(MediaCatalog.avg_engagement.desc()).limit(10)
    )
    top_media = [
        {
            "id": m.id,
            "filename": m.filename,
            "engagement": m.avg_engagement,
        }
        for m in media_result.scalars().all()
    ]

    # Build and run Claude prompt
    prompt = _build_prompt(
        start=req.date_range_start,
        end=req.date_range_end,
        platforms=req.platforms,
        pillars=pillars,
        festivals=festivals,
        knowledge=knowledge,
        top_media=top_media,
        constraints=req.constraints,
    )

    try:
        raw_response = _run_claude(prompt)
    except Exception as e:
        logger.error("Calendar planning failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"AI planning failed: {e}",
        )

    # Parse Claude response
    try:
        # Strip markdown fences if present
        text = raw_response
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        slots_data = json.loads(text)
    except (json.JSONDecodeError, IndexError):
        logger.error("Failed to parse Claude response: %s", raw_response[:500])
        raise HTTPException(
            status_code=500,
            detail="AI returned invalid JSON. Please try again.",
        )

    # Save to database
    plan = CalendarPlan(
        date_range_start=datetime.strptime(req.date_range_start, "%Y-%m-%d"),
        date_range_end=datetime.strptime(req.date_range_end, "%Y-%m-%d"),
        platforms=json.dumps(req.platforms),
        plan_data=json.dumps(slots_data),
        status="draft",
    )
    session.add(plan)
    await session.commit()
    await session.refresh(plan)

    # Build response
    slots = [
        CalendarPlanSlot(
            date=s.get("date", ""),
            time=s.get("time"),
            pillar=s.get("pillar"),
            topic=s.get("topic"),
            content_idea=s.get("content_idea", ""),
            recommended_media_id=s.get("recommended_media_id"),
            target_platforms=s.get("target_platforms", []),
        )
        for s in slots_data
    ]

    return CalendarPlanResponse(
        id=plan.id,
        date_range_start=req.date_range_start,
        date_range_end=req.date_range_end,
        platforms=req.platforms,
        slots=slots,
        status=plan.status,
        created_at=plan.created_at.isoformat(),
    )
