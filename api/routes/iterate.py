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


@router.post("/iterate/revert", response_model=IterateResponse)
async def revert_caption(
    content_row_id: int,
    platform: str,
    iteration_id: int | None = None,
    repo: ContentRepository = Depends(get_content_repo),
):
    """Revert a caption to a previous version.

    If iteration_id is provided, reverts to that iteration's old_caption.
    If omitted, reverts to the very first (original) caption.
    """
    row = await repo.get_content_row(content_row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Content row not found")

    iterations = await repo.get_iterations(content_row_id)
    platform_iters = [i for i in iterations if i.platform == platform]
    if not platform_iters:
        raise HTTPException(status_code=404, detail="No iteration history for this platform")

    if iteration_id is not None:
        # Revert to a specific iteration's old_caption
        target = next((i for i in platform_iters if i.id == iteration_id), None)
        if not target:
            raise HTTPException(status_code=404, detail="Iteration not found")
        revert_to = target.old_caption
    else:
        # Revert to original — the oldest iteration's old_caption
        oldest = min(platform_iters, key=lambda i: i.id)
        revert_to = oldest.old_caption

    if revert_to is None:
        raise HTTPException(status_code=400, detail="No original caption to revert to")

    # Save the revert as an iteration for audit trail
    captions = _parse_json_field(row.captions)
    current_caption = captions.get(platform)

    iteration = await repo.add_iteration(
        {
            "content_row_id": content_row_id,
            "platform": platform,
            "old_caption": current_caption,
            "new_caption": revert_to,
            "refinement_instruction": "Reverted to original"
            if iteration_id is None
            else f"Reverted to iteration {iteration_id}",
            "mode": "revert",
        }
    )

    # Update content row
    captions[platform] = revert_to
    await repo.update_captions(content_row_id, json.dumps(captions))

    return IterateResponse(caption=revert_to, iteration_id=iteration.id)


@router.delete("/iterations/{iteration_id}")
async def delete_iteration(
    iteration_id: int,
    repo: ContentRepository = Depends(get_content_repo),
):
    """Delete a single iteration log entry."""
    deleted = await repo.delete_iteration(iteration_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Iteration not found")
    return {"ok": True}
