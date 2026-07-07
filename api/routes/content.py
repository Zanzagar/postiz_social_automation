"""Content reading and action endpoints."""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from PIL import Image

from api.auth import get_current_user
from api.dependencies import get_content_repo, get_postiz_client, get_sheets_client
from api.models import MediaAdapted, MediaCatalog
from api.repositories.content import ContentRepository
from api.routes.media import PLATFORM_DIMENSIONS, _smart_crop
from api.schemas import (
    AltTextRequest,
    ApproveResponse,
    CalendarEntry,
    CalendarResponse,
    ContentRowResponse,
    EditCaptionsRequest,
    RequireReviewRequest,
    SuggestionResponse,
)
from api.services.auto_publish import compute_auto_publish_at, no_alt_block
from content_engine.postiz import PostizAPIError

logger = logging.getLogger(__name__)

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
        require_review=bool(row.require_review),
        held_at=row.held_at,
        alt_text=row.alt_text,
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
    schedule: bool = False,
    repo: ContentRepository = Depends(get_content_repo),
    postiz=Depends(get_postiz_client),
):
    """Approve a draft and create Postiz posts for all enabled platforms.

    Computes auto_publish_at from the publish config (null if ineligible).
    With schedule=true the caller explicitly requests scheduling/release,
    which is blocked with 422 when the row has media but no alt text.
    """
    row = await repo.get_content_row(row_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Row {row_id} not found.")

    if schedule and no_alt_block(row):
        raise HTTPException(status_code=422, detail="alt_text_required")

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

    # Auto-publish eligibility (single source of truth in services/auto_publish)
    now = datetime.now(UTC)
    configs = await repo.get_publish_configs()
    auto_at = compute_auto_publish_at(row, configs, now)
    if schedule and auto_at is None and not row.require_review:
        # Explicit release request for a config-ineligible row: release on
        # the next loop cycle.
        auto_at = now
    row.auto_publish_at = auto_at
    await repo.session.commit()

    return ApproveResponse(success=True, postiz_ids=draft_ids)


# --- Auto-publish workflow actions ---


@router.post("/content/{row_id}/hold", response_model=ContentRowResponse)
async def hold_content(row_id: int, repo: ContentRepository = Depends(get_content_repo)):
    """Hold a row: a held row NEVER auto-releases. Idempotent."""
    row = await repo.get_content_row(row_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Row {row_id} not found.")

    if row.held_at is None:
        row.held_at = datetime.now(UTC)
        await repo.session.commit()
    return _row_to_response(row)


@router.post("/content/{row_id}/resume", response_model=ContentRowResponse)
async def resume_content(row_id: int, repo: ContentRepository = Depends(get_content_repo)):
    """Clear a hold; recompute auto_publish_at for approved rows if eligible."""
    row = await repo.get_content_row(row_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Row {row_id} not found.")

    row.held_at = None
    if row.status == "approved":
        configs = await repo.get_publish_configs()
        row.auto_publish_at = compute_auto_publish_at(row, configs, datetime.now(UTC))
    await repo.session.commit()
    return _row_to_response(row)


@router.put("/content/{row_id}/require-review", response_model=ContentRowResponse)
async def set_require_review(
    row_id: int,
    req: RequireReviewRequest,
    repo: ContentRepository = Depends(get_content_repo),
):
    """Set the require-review flag; a require-review post never auto-releases."""
    row = await repo.get_content_row(row_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Row {row_id} not found.")

    row.require_review = req.require_review
    if req.require_review:
        row.auto_publish_at = None
    await repo.session.commit()
    return _row_to_response(row)


@router.put("/content/{row_id}/alt-text", response_model=ContentRowResponse)
async def set_alt_text(
    row_id: int,
    req: AltTextRequest,
    repo: ContentRepository = Depends(get_content_repo),
):
    """Set alt text for a row's media (clears the NO-ALT publish block)."""
    row = await repo.get_content_row(row_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Row {row_id} not found.")

    row.alt_text = req.alt_text
    await repo.session.commit()
    return _row_to_response(row)


@router.put("/content/{row_id}/attach-media")
async def attach_media(
    row_id: int,
    media_id: int,
    repo: ContentRepository = Depends(get_content_repo),
):
    """Attach a media catalog item to a content row and auto-adapt."""
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

    # Auto-adapt media for content row's platforms
    adapted_count = 0
    platforms = _parse_json_field(row.platforms)
    enabled_platforms = [p for p, on in platforms.items() if on]

    media = await repo.session.get(MediaCatalog, media_id)
    if media and media.local_path:
        src_path = Path(media.local_path)
        if src_path.exists():
            adapted_dir = src_path.parent / "adapted"
            adapted_dir.mkdir(parents=True, exist_ok=True)
            try:
                with Image.open(src_path) as src_img:
                    for platform in enabled_platforms:
                        dims = PLATFORM_DIMENSIONS.get(platform, {})
                        for fmt, (tw, th) in dims.items():
                            out_name = f"{media_id}_{platform}_{fmt}.jpg"
                            out_path = adapted_dir / out_name
                            adapted_img = _smart_crop(src_img, tw, th)
                            adapted_img.save(out_path, "JPEG", quality=90)
                            repo.session.add(
                                MediaAdapted(
                                    media_id=media_id,
                                    platform=platform,
                                    format=fmt,
                                    adapted_path=str(out_path),
                                    width=tw,
                                    height=th,
                                )
                            )
                            adapted_count += 1
            except Exception:
                logger.warning("Auto-adapt failed for media %d", media_id, exc_info=True)

    await repo.session.commit()
    return {
        "media_catalog_ids": current_ids,
        "adapted_count": adapted_count,
    }


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
