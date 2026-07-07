"""Content generation endpoints with SSE streaming."""

import asyncio
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from api.auth import get_current_user
from api.dependencies import get_caption_generator, get_content_repo
from api.repositories.content import ContentRepository
from api.schemas import GenerateRequest, RepromptRequest
from content_engine.models import ContentRow, ContentStatus, Platform
from content_engine.validator import validate_external_url

router = APIRouter(prefix="/api", tags=["generate"], dependencies=[Depends(get_current_user)])


def _build_content_row(req: GenerateRequest | RepromptRequest) -> ContentRow:
    """Build a ContentRow from request data."""
    platforms = {Platform(p): True for p in req.platforms}
    media = req.media_url
    if media:
        try:
            validate_external_url(media)
        except ValueError:
            media = None

    pillar = None
    if hasattr(req, "content_pillar") and req.content_pillar:
        pillar = req.content_pillar

    return ContentRow(
        row_number=0,
        date=datetime.fromisoformat(req.scheduled_date),
        raw_text=req.raw_text,
        media_url=media,
        platforms=platforms,
        status=ContentStatus.DRAFT,
        captions={Platform(p): None for p in req.platforms},
        content_pillar=pillar,
    )


async def _persist_generated(
    req: GenerateRequest | RepromptRequest,
    captions: dict,
    repo: ContentRepository,
) -> int:
    """Save generated content to SQLite. Returns the new row ID."""
    platforms_json = json.dumps({str(p): True for p in req.platforms})
    captions_json = json.dumps({str(k): v for k, v in captions.items()})

    row = await repo.create_content_row(
        {
            "raw_text": req.raw_text,
            "date": datetime.fromisoformat(req.scheduled_date),
            "media_url": req.media_url if req.media_url else None,
            "platforms": platforms_json,
            "captions": captions_json,
            "status": "draft",
            "source": "generated",
            "pillar": req.content_pillar if hasattr(req, "content_pillar") else None,
        }
    )
    return row.id


@router.post("/generate")
async def generate(
    req: GenerateRequest,
    generator=Depends(get_caption_generator),
    repo: ContentRepository = Depends(get_content_repo),
):
    """Stream caption generation progress via SSE."""

    is_demo = hasattr(generator, "__class__") and "Demo" in generator.__class__.__name__

    async def event_stream():
        try:
            yield json.dumps({"status": "validating"})
            if is_demo:
                await asyncio.sleep(0.5)

            row = _build_content_row(req)

            yield json.dumps({"status": "generating"})
            if is_demo:
                await asyncio.sleep(1.5)

            captions = await asyncio.to_thread(generator.generate_captions, row)
            captions_map = {str(k): v for k, v in captions.items()}

            # Per-platform progress events. Generation is a single Claude
            # call covering all platforms (splitting it would multiply
            # calls and change output quality), so these are emitted as
            # each caption becomes available post-parse — the frontend
            # contract sees zero+ platform_done events before done.
            for platform, caption in captions_map.items():
                yield json.dumps(
                    {"status": "platform_done", "platform": platform, "caption": caption}
                )

            row_id = await _persist_generated(req, captions, repo)

            yield json.dumps(
                {
                    "status": "done",
                    "row_id": row_id,
                    "captions": captions_map,
                }
            )
        except Exception as e:
            yield json.dumps({"status": "error", "message": str(e)})

    return EventSourceResponse(event_stream())


@router.post("/generate-sync")
async def generate_sync(
    req: GenerateRequest,
    persist: bool = True,
    skip_ai: bool = False,
    generator=Depends(get_caption_generator),
    repo: ContentRepository = Depends(get_content_repo),
):
    """Non-streaming caption generation (works through proxies).

    Set persist=false to generate captions without creating a new content row.
    Set skip_ai=true to save the raw text as-is for all platforms (no AI).
    """
    if skip_ai:
        captions = {p: req.raw_text for p in req.platforms}
    else:
        row = _build_content_row(req)
        try:
            captions = await asyncio.to_thread(generator.generate_captions, row)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        captions = {str(k): v for k, v in captions.items()}

    result: dict = {"captions": captions}
    if persist:
        row_id = await _persist_generated(req, captions, repo)
        result["row_id"] = row_id
    return result


@router.post("/reprompt")
async def reprompt(
    req: RepromptRequest,
    generator=Depends(get_caption_generator),
    repo: ContentRepository = Depends(get_content_repo),
):
    """Regenerate captions with feedback."""
    row = _build_content_row(req)
    try:
        captions = await asyncio.to_thread(generator.generate_captions, row, req.feedback)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    row_id = await _persist_generated(req, captions, repo)
    return {"row_id": row_id, "captions": {str(k): v for k, v in captions.items()}}
