"""AI content iteration endpoints."""

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException

from api.auth import get_current_user
from api.dependencies import get_caption_generator, get_content_repo
from api.repositories.content import ContentRepository
from api.schemas import IterateRequest, IterateResponse, IterationResponse

router = APIRouter(prefix="/api", tags=["iterate"], dependencies=[Depends(get_current_user)])


def _parse_json_field(value: str | None) -> dict:
    if not value:
        return {}
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {}


@router.post("/iterate", response_model=IterateResponse)
async def iterate_caption(
    req: IterateRequest,
    repo: ContentRepository = Depends(get_content_repo),
    generator=Depends(get_caption_generator),
):
    """Regenerate a single platform caption based on user instruction."""
    row = await repo.get_content_row(req.content_row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Content row not found")

    captions = _parse_json_field(row.captions)
    old_caption = captions.get(req.platform)

    # Call AI to iterate on the caption (run in thread to avoid blocking event loop)
    new_caption = await asyncio.to_thread(
        generator.iterate_single_caption,
        original_caption=old_caption,
        platform=req.platform,
        instruction=req.instruction,
        raw_text=row.raw_text,
        pillar=row.pillar,
    )

    # Save iteration history
    iteration = await repo.add_iteration(
        {
            "content_row_id": req.content_row_id,
            "platform": req.platform,
            "old_caption": old_caption,
            "new_caption": new_caption,
            "refinement_instruction": req.instruction,
            "mode": req.mode,
        }
    )

    # Update content row with new caption
    captions[req.platform] = new_caption
    await repo.update_captions(req.content_row_id, json.dumps(captions))

    return IterateResponse(caption=new_caption, iteration_id=iteration.id)


@router.get("/iterations/{content_id}", response_model=list[IterationResponse])
async def get_iterations(
    content_id: int,
    repo: ContentRepository = Depends(get_content_repo),
):
    """Return iteration history for a content row."""
    iterations = await repo.get_iterations(content_id)
    return [
        IterationResponse(
            id=i.id,
            content_row_id=i.content_row_id,
            platform=i.platform,
            old_caption=i.old_caption,
            new_caption=i.new_caption,
            refinement_instruction=i.refinement_instruction,
            mode=i.mode,
            created_by=i.created_by,
            created_at=i.created_at,
        )
        for i in iterations
    ]
