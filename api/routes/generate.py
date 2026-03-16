"""Content generation endpoints with SSE streaming."""

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from api.auth import get_current_user
from api.dependencies import get_caption_generator
from api.schemas import GenerateRequest, RepromptRequest
from content_engine.models import ContentRow, ContentStatus, Platform

router = APIRouter(prefix="/api", tags=["generate"], dependencies=[Depends(get_current_user)])


def _build_content_row(req: GenerateRequest | RepromptRequest) -> ContentRow:
    """Build a ContentRow from request data."""
    from datetime import datetime

    platforms = {Platform(p): True for p in req.platforms}
    return ContentRow(
        row_number=0,
        date=datetime.fromisoformat(req.scheduled_date),
        raw_text=req.raw_text,
        media_url=req.media_url,
        platforms=platforms,
        status=ContentStatus.DRAFT,
        captions={Platform(p): None for p in req.platforms},
    )


@router.post("/generate")
async def generate(req: GenerateRequest, generator=Depends(get_caption_generator)):
    """Stream caption generation progress via SSE."""

    async def event_stream():
        try:
            yield json.dumps({"status": "validating"})

            row = _build_content_row(req)

            yield json.dumps({"status": "generating"})

            captions = await asyncio.to_thread(generator.generate_captions, row)

            yield json.dumps(
                {
                    "status": "complete",
                    "captions": {str(k): v for k, v in captions.items()},
                }
            )
        except Exception as e:
            yield json.dumps({"status": "error", "message": str(e)})

    return EventSourceResponse(event_stream())


@router.post("/reprompt")
async def reprompt(req: RepromptRequest, generator=Depends(get_caption_generator)):
    """Regenerate captions with feedback."""
    row = _build_content_row(req)
    try:
        captions = await asyncio.to_thread(generator.generate_captions, row, req.feedback)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"captions": {str(k): v for k, v in captions.items()}}
