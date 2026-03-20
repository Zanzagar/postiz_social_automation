"""AI calendar planning endpoints — generate content calendars using Claude."""

import json
import logging
import subprocess
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from api.dependencies import get_db
from api.models import CalendarPlan, ContentRow, MediaCatalog, Pillar, WebKnowledge
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


def _plan_to_response(plan: CalendarPlan) -> CalendarPlanResponse:
    """Convert a CalendarPlan DB record to response model."""
    slots_data = json.loads(plan.plan_data) if plan.plan_data else []
    platforms = json.loads(plan.platforms) if plan.platforms else []
    return CalendarPlanResponse(
        id=plan.id,
        date_range_start=plan.date_range_start.strftime("%Y-%m-%d"),
        date_range_end=plan.date_range_end.strftime("%Y-%m-%d"),
        platforms=platforms,
        slots=[
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
        ],
        status=plan.status,
        created_at=plan.created_at.isoformat(),
    )


# ── View ─────────────────────────────────────────────────────────────


@router.get("/plan/{plan_id}")
async def get_plan(
    plan_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Get a calendar plan by ID with full slot details."""
    result = await session.execute(select(CalendarPlan).where(CalendarPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return _plan_to_response(plan)


# ── List ─────────────────────────────────────────────────────────────


@router.get("/plans")
async def list_plans(
    status: str | None = None,
    session: AsyncSession = Depends(get_db),
):
    """List all calendar plans, optionally filtered by status."""
    query = select(CalendarPlan).order_by(CalendarPlan.created_at.desc())
    if status:
        query = query.where(CalendarPlan.status == status)
    result = await session.execute(query)
    plans = result.scalars().all()
    return {"plans": [_plan_to_response(p) for p in plans]}


# ── Approve ──────────────────────────────────────────────────────────


class ApproveRequest(BaseModel):
    slot_indices: list[int] | None = None
    auto_schedule: bool = False


@router.post("/plan/{plan_id}/approve")
async def approve_plan(
    plan_id: int,
    req: ApproveRequest,
    session: AsyncSession = Depends(get_db),
):
    """Approve plan slots and create content rows from them."""
    result = await session.execute(select(CalendarPlan).where(CalendarPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if plan.status == "approved":
        raise HTTPException(status_code=400, detail="Plan already fully approved")

    slots_data = json.loads(plan.plan_data) if plan.plan_data else []
    indices = req.slot_indices if req.slot_indices is not None else list(range(len(slots_data)))

    content_row_ids = []
    for idx in indices:
        if idx < 0 or idx >= len(slots_data):
            continue
        slot = slots_data[idx]

        # Build platforms dict
        platforms = {p: True for p in slot.get("target_platforms", [])}

        # Parse date
        slot_date = None
        if slot.get("date"):
            try:
                slot_date = datetime.strptime(slot["date"], "%Y-%m-%d")
            except ValueError:
                pass

        # Media catalog IDs
        media_ids = None
        if slot.get("recommended_media_id"):
            media_ids = json.dumps([slot["recommended_media_id"]])

        row = ContentRow(
            date=slot_date,
            pillar=slot.get("pillar"),
            raw_text=slot.get("content_idea", ""),
            platforms=json.dumps(platforms),
            captions=json.dumps({}),
            status="draft",
            source="plan",
            media_catalog_ids=media_ids,
        )
        session.add(row)
        await session.flush()
        content_row_ids.append(row.id)

    # Update plan status
    if req.slot_indices is None or len(indices) >= len(slots_data):
        plan.status = "approved"
    else:
        plan.status = "partial"

    await session.commit()

    return {
        "created_count": len(content_row_ids),
        "content_row_ids": content_row_ids,
    }


# ── Delete ───────────────────────────────────────────────────────────


@router.delete("/plan/{plan_id}")
async def delete_plan(
    plan_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Delete a calendar plan (draft only)."""
    result = await session.execute(select(CalendarPlan).where(CalendarPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if plan.status != "draft":
        raise HTTPException(
            status_code=400,
            detail="Only draft plans can be deleted",
        )

    await session.delete(plan)
    await session.commit()
    return {"deleted": True, "id": plan_id}
