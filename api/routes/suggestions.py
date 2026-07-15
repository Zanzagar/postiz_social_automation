"""SQLite-backed content suggestion endpoints (festival, pillar gap, template)."""

from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from api.dependencies import get_content_repo, get_db
from api.models import Suggestion
from api.repositories.content import ContentRepository
from api.schemas import (
    SuggestionDismissResponse,
    SuggestionDraftResponse,
    SuggestionItem,
    SuggestionsResponse,
)
from api.services.suggestion_generator import refresh_suggestions

router = APIRouter(prefix="/api", tags=["suggestions"], dependencies=[Depends(get_current_user)])


def _today() -> date:
    """Current date — module-level seam so tests can freeze the clock."""
    return date.today()


def _to_item(suggestion: Suggestion, today: date) -> SuggestionItem:
    """Convert a Suggestion ORM row to its API representation."""
    suggested = suggestion.suggested_date
    return SuggestionItem(
        id=suggestion.id,
        type=suggestion.type,
        title=suggestion.title,
        note=suggestion.note,
        pillar=suggestion.pillar,
        date=suggested.isoformat() if suggested else None,
        days_until=(suggested - today).days if suggested else None,
        status=suggestion.status,
    )


async def _list_suggestions(session: AsyncSession, status: str, today: date) -> SuggestionsResponse:
    """Return suggestions filtered by status: dated by date asc, then undated."""
    stmt = select(Suggestion)
    if status != "all":
        stmt = stmt.where(Suggestion.status == status)
    result = await session.execute(stmt)
    rows = list(result.scalars().all())

    dated = sorted(
        (r for r in rows if r.suggested_date is not None), key=lambda r: r.suggested_date
    )
    undated = sorted(
        (r for r in rows if r.suggested_date is None),
        key=lambda r: r.created_at,
        reverse=True,
    )
    return SuggestionsResponse(suggestions=[_to_item(r, today) for r in dated + undated])


@router.get("/suggestions", response_model=SuggestionsResponse)
async def get_suggestions(status: str = "suggested", session: AsyncSession = Depends(get_db)):
    """Return suggestions filtered by status ("all" returns everything)."""
    return await _list_suggestions(session, status, _today())


@router.post("/suggestions/refresh", response_model=SuggestionsResponse)
async def refresh(session: AsyncSession = Depends(get_db)):
    """Regenerate suggestions and return the current suggested set."""
    today = _today()
    await refresh_suggestions(session, today)
    return await _list_suggestions(session, "suggested", today)


@router.post("/suggestions/{suggestion_id}/dismiss", response_model=SuggestionDismissResponse)
async def dismiss_suggestion(suggestion_id: int, session: AsyncSession = Depends(get_db)):
    """Mark a suggestion dismissed so refresh never resurrects it."""
    suggestion = await session.get(Suggestion, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail=f"Suggestion {suggestion_id} not found.")
    suggestion.status = "dismissed"
    await session.commit()
    return SuggestionDismissResponse(id=suggestion.id, status="dismissed")


@router.post("/suggestions/{suggestion_id}/draft", response_model=SuggestionDraftResponse)
async def draft_suggestion(
    suggestion_id: int,
    session: AsyncSession = Depends(get_db),
    repo: ContentRepository = Depends(get_content_repo),
):
    """Create a draft ContentRow from a suggestion and link the two."""
    suggestion = await session.get(Suggestion, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail=f"Suggestion {suggestion_id} not found.")

    row_data: dict = {
        "raw_text": f"{suggestion.title} — {suggestion.note}",
        "status": "draft",
        "pillar": suggestion.pillar,
        "source": "suggestion",
    }
    if suggestion.suggested_date is not None:
        row_data["date"] = datetime.combine(suggestion.suggested_date, time.min)
    row = await repo.create_content_row(row_data)

    suggestion.status = "drafted"
    suggestion.content_row_id = row.id
    await session.commit()
    return SuggestionDraftResponse(id=suggestion.id, status="drafted", content_row_id=row.id)
