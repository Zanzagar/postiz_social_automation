"""Postiz integration endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from api.auth import get_current_user
from api.dependencies import get_postiz_client
from api.schemas import IntegrationResponse, PostizDraftResponse, SendToPostizRequest
from content_engine.postiz import MediaValidationError, PostizAPIError

router = APIRouter(prefix="/api", tags=["postiz"], dependencies=[Depends(get_current_user)])


@router.post("/send-to-postiz", response_model=PostizDraftResponse)
async def send_to_postiz(req: SendToPostizRequest, postiz=Depends(get_postiz_client)):
    """Create draft posts in Postiz for each platform."""
    try:
        integrations = postiz.list_integrations()
    except PostizAPIError as e:
        raise HTTPException(status_code=502, detail=f"Postiz API error: {e}")

    # Map platform names to integration IDs
    platform_id_map = {}
    for integration in integrations:
        plat = integration.get("identifier", "").lower()
        if plat in req.captions:
            platform_id_map[plat] = integration["id"]

    draft_ids = []
    platforms_sent = []
    for platform, caption in req.captions.items():
        integration_id = platform_id_map.get(platform)
        if not integration_id:
            continue
        try:
            result = postiz.create_draft_post(
                content=caption,
                platform_ids=[integration_id],
                media_url=req.media_url,
                scheduled_at=req.scheduled_at,
            )
            if result and "id" in result:
                draft_ids.append(result["id"])
                platforms_sent.append(platform)
        except (PostizAPIError, MediaValidationError) as e:
            raise HTTPException(status_code=502, detail=f"Failed for {platform}: {e}")

    return PostizDraftResponse(draft_ids=draft_ids, platforms=platforms_sent)


@router.get("/integrations", response_model=list[IntegrationResponse])
async def list_integrations(postiz=Depends(get_postiz_client)):
    """Return list of connected Postiz integrations."""
    try:
        integrations = postiz.list_integrations()
    except PostizAPIError as e:
        raise HTTPException(status_code=502, detail=f"Postiz API error: {e}")

    return [
        IntegrationResponse(
            id=i.get("id", ""),
            platform=i.get("identifier", "unknown"),
            name=i.get("name", i.get("identifier", "unknown")),
        )
        for i in integrations
    ]
