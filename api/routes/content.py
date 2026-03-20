"""Content reading and action endpoints."""

import json

from fastapi import APIRouter, Depends, HTTPException

from api.auth import get_current_user
from api.dependencies import get_content_repo, get_postiz_client, get_sheets_client
from api.repositories.content import ContentRepository
from api.schemas import (
    ApproveResponse,
    CalendarEntry,
    CalendarResponse,
    ContentRowResponse,
    EditCaptionsRequest,
    SuggestionResponse,
)
from content_engine.postiz import PostizAPIError

router = APIRouter(prefix="/api", tags=["content"], dependencies=[Depends(get_current_user)])


def _parse_json_field(value: str | None) -> dict:
    """Parse a JSON string field, returning empty dict if None/empty."""
    if not value:
        return {}
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {}


def _row_to_response(row) -> ContentRowResponse:
    """Convert a SQLAlchemy ContentRow to API response."""
    platforms = _parse_json_field(row.platforms)
    captions = _parse_json_field(row.captions)

    return ContentRowResponse(
        row_number=row.id,
        date=row.date or row.created_at,
        content_pillar=row.pillar,
        raw_text=row.raw_text,
        media_url=row.media_url,
        platforms=platforms,
        status=row.status or "draft",
        captions=captions,
        feedback=row.feedback,
        postiz_ids=row.postiz_ids,
        posted_at=row.posted_at,
        error_msg=None,
        source=row.source or "manual",
        auto_publish_at=row.auto_publish_at,
    )


def _row_to_calendar_entry(row) -> CalendarEntry:
    """Convert a SQLAlchemy ContentRow to a CalendarEntry."""
    platforms = _parse_json_field(row.platforms)
    captions = _parse_json_field(row.captions)

    return CalendarEntry(
        row_number=row.id,
        date=row.date or row.created_at,
        content_pillar=row.pillar,
        raw_text=row.raw_text,
        status=row.status or "draft",
        platforms=platforms,
        captions=captions,
    )


@router.get("/drafts", response_model=list[ContentRowResponse])
async def get_drafts(repo: ContentRepository = Depends(get_content_repo)):
    """Return all pre-published rows (draft, pending_approval, approved)."""
    rows = []
    for status in ["draft", "pending_approval", "approved"]:
        rows.extend(await repo.get_rows_by_status(status))
    return [_row_to_response(r) for r in rows]


@router.get("/calendar", response_model=CalendarResponse)
async def get_calendar(repo: ContentRepository = Depends(get_content_repo)):
    """Return all content as calendar entries."""
    entries = []
    for status in ["draft", "pending_approval", "approved", "scheduled", "posted"]:
        rows = await repo.get_rows_by_status(status)
        entries.extend([_row_to_calendar_entry(r) for r in rows])
    entries.sort(key=lambda e: e.date)
    return CalendarResponse(entries=entries, total=len(entries))


@router.get("/suggestions", response_model=list[SuggestionResponse])
async def get_suggestions(status: str | None = None, sheets=Depends(get_sheets_client)):
    """Return suggestions, optionally filtered by status.

    Note: Suggestions still use Sheets until a Suggestion table is added.
    """
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


@router.get("/content/{row_id}", response_model=ContentRowResponse)
async def get_content_row(row_id: int, repo: ContentRepository = Depends(get_content_repo)):
    """Return a single content row by ID."""
    row = await repo.get_content_row(row_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Row {row_id} not found.")
    return _row_to_response(row)


@router.post("/drafts/{row_id}/edit", response_model=ContentRowResponse)
async def edit_draft(
    row_id: int,
    req: EditCaptionsRequest,
    repo: ContentRepository = Depends(get_content_repo),
):
    """Update captions for a draft row."""
    row = await repo.get_content_row(row_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Row {row_id} not found.")

    captions_json = json.dumps(req.captions)
    await repo.update_captions(row_id, captions_json)

    if req.platforms is not None:
        platforms_json = json.dumps(req.platforms)
        await repo.update_platforms(row_id, platforms_json)

    updated = await repo.get_content_row(row_id)
    return _row_to_response(updated)


@router.post("/drafts/{row_id}/approve", response_model=ApproveResponse)
async def approve_draft(
    row_id: int,
    repo: ContentRepository = Depends(get_content_repo),
    postiz=Depends(get_postiz_client),
):
    """Approve a draft and create Postiz posts for all enabled platforms."""
    row = await repo.get_content_row(row_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Row {row_id} not found.")

    await repo.update_status(row_id, "approved")

    # Create Postiz drafts
    try:
        integrations = postiz.list_integrations()
    except PostizAPIError as e:
        raise HTTPException(status_code=502, detail=f"Postiz error: {e}")

    platform_id_map = {i.get("identifier", "").lower(): i["id"] for i in integrations}

    platforms = _parse_json_field(row.platforms)
    captions = _parse_json_field(row.captions)

    draft_ids = []
    enabled = [p for p, on in platforms.items() if on]
    for platform in enabled:
        caption = captions.get(platform)
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


@router.put("/content/{row_id}/attach-media")
async def attach_media(
    row_id: int,
    media_id: int,
    repo: ContentRepository = Depends(get_content_repo),
):
    """Attach a media catalog item to a content row."""
    row = await repo.get_content_row(row_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Row {row_id} not found.")

    current_ids: list[int] = []
    if row.media_catalog_ids:
        try:
            current_ids = json.loads(row.media_catalog_ids)
        except (json.JSONDecodeError, TypeError):
            pass

    if media_id not in current_ids:
        current_ids.append(media_id)

    row.media_catalog_ids = json.dumps(current_ids)
    await repo.session.commit()
    return {"media_catalog_ids": current_ids}


@router.put("/content/{row_id}/detach-media")
async def detach_media(
    row_id: int,
    media_id: int,
    repo: ContentRepository = Depends(get_content_repo),
):
    """Detach a media catalog item from a content row."""
    row = await repo.get_content_row(row_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Row {row_id} not found.")

    current_ids: list[int] = []
    if row.media_catalog_ids:
        try:
            current_ids = json.loads(row.media_catalog_ids)
        except (json.JSONDecodeError, TypeError):
            pass

    current_ids = [mid for mid in current_ids if mid != media_id]
    row.media_catalog_ids = json.dumps(current_ids) if current_ids else None
    await repo.session.commit()
    return {"media_catalog_ids": current_ids}
