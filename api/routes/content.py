"""Content reading and action endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from api.auth import get_current_user
from api.dependencies import get_postiz_client, get_sheets_client
from api.schemas import (
    ApproveResponse,
    CalendarEntry,
    CalendarResponse,
    ContentRowResponse,
    EditCaptionsRequest,
    SuggestionResponse,
)
from content_engine.models import ContentStatus, Platform
from content_engine.postiz import PostizAPIError

router = APIRouter(prefix="/api", tags=["content"], dependencies=[Depends(get_current_user)])


def _row_to_response(row) -> ContentRowResponse:
    """Convert a ContentRow model to API response."""
    return ContentRowResponse(
        row_number=row.row_number,
        date=row.date,
        content_pillar=str(row.content_pillar) if row.content_pillar else None,
        raw_text=row.raw_text,
        media_url=str(row.media_url) if row.media_url else None,
        platforms={str(k): v for k, v in row.platforms.items()},
        status=str(row.status),
        captions={str(k): v for k, v in row.captions.items()},
        feedback=row.feedback,
        postiz_ids=row.postiz_ids,
        posted_at=row.posted_at,
        error_msg=row.error_msg,
        source=row.source,
    )


@router.get("/drafts", response_model=list[ContentRowResponse])
async def get_drafts(sheets=Depends(get_sheets_client)):
    """Return rows pending approval."""
    rows = sheets.get_rows_by_status(ContentStatus.PENDING_APPROVAL)
    return [_row_to_response(r) for r in rows]


@router.get("/calendar", response_model=CalendarResponse)
async def get_calendar(sheets=Depends(get_sheets_client)):
    """Return calendar entries (approved, scheduled, posted)."""
    entries = []
    for status in [ContentStatus.APPROVED, ContentStatus.SCHEDULED, ContentStatus.POSTED]:
        rows = sheets.get_rows_by_status(status)
        for row in rows:
            entries.append(
                CalendarEntry(
                    row_number=row.row_number,
                    date=row.date,
                    content_pillar=str(row.content_pillar) if row.content_pillar else None,
                    raw_text=row.raw_text,
                    status=str(row.status),
                    platforms={str(k): v for k, v in row.platforms.items()},
                    captions={str(k): v for k, v in row.captions.items()},
                )
            )
    entries.sort(key=lambda e: e.date)
    return CalendarResponse(entries=entries, total=len(entries))


@router.get("/suggestions", response_model=list[SuggestionResponse])
async def get_suggestions(status: str | None = None, sheets=Depends(get_sheets_client)):
    """Return suggestions, optionally filtered by status."""
    suggestions = sheets.get_suggestions(status=status)
    return [
        SuggestionResponse(
            suggested_date=s.suggested_date,
            content_idea=s.content_idea,
            suggested_pillar=str(s.suggested_pillar),
            rationale=s.rationale,
            media_suggestion=s.media_suggestion,
            status=s.status,
        )
        for s in suggestions
    ]


@router.get("/content/{row_number}", response_model=ContentRowResponse)
async def get_content_row(row_number: int, sheets=Depends(get_sheets_client)):
    """Return a single content row by row number."""
    rows = sheets.get_all_content_rows()
    for row in rows:
        if row.row_number == row_number:
            return _row_to_response(row)
    raise HTTPException(status_code=404, detail=f"Row {row_number} not found.")


@router.post("/drafts/{row_number}/edit", response_model=ContentRowResponse)
async def edit_draft(row_number: int, req: EditCaptionsRequest, sheets=Depends(get_sheets_client)):
    """Update captions for a draft row."""
    captions = {Platform(k): v for k, v in req.captions.items()}
    sheets.update_captions(row_number, captions)
    # Re-fetch updated row
    rows = sheets.get_all_content_rows()
    for row in rows:
        if row.row_number == row_number:
            return _row_to_response(row)
    raise HTTPException(status_code=404, detail=f"Row {row_number} not found after edit.")


@router.post("/drafts/{row_number}/approve", response_model=ApproveResponse)
async def approve_draft(
    row_number: int,
    sheets=Depends(get_sheets_client),
    postiz=Depends(get_postiz_client),
):
    """Approve a draft and create Postiz posts for all enabled platforms."""
    rows = sheets.get_all_content_rows()
    row = None
    for r in rows:
        if r.row_number == row_number:
            row = r
            break
    if not row:
        raise HTTPException(status_code=404, detail=f"Row {row_number} not found.")

    sheets.update_status(row_number, ContentStatus.APPROVED)

    # Create Postiz drafts
    try:
        integrations = postiz.list_integrations()
    except PostizAPIError as e:
        raise HTTPException(status_code=502, detail=f"Postiz error: {e}")

    platform_id_map = {i.get("identifier", "").lower(): i["id"] for i in integrations}

    draft_ids = []
    enabled = [str(p) for p, on in row.platforms.items() if on]
    for platform in enabled:
        caption = row.captions.get(Platform(platform))
        integration_id = platform_id_map.get(platform)
        if not caption or not integration_id:
            continue
        try:
            result = postiz.create_draft_post(content=caption, platform_ids=[integration_id])
            if result and "id" in result:
                draft_ids.append(result["id"])
        except PostizAPIError:
            pass

    return ApproveResponse(success=True, postiz_ids=draft_ids)
