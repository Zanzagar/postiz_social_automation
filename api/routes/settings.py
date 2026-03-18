"""Auto-publish configuration endpoints."""

import json

from fastapi import APIRouter, Depends

from api.auth import get_current_user
from api.dependencies import get_content_repo
from api.repositories.content import ContentRepository
from api.schemas import (
    PlatformPublishConfig,
    PublishConfigResponse,
    UpdatePublishConfigRequest,
)

router = APIRouter(
    prefix="/api/settings", tags=["settings"], dependencies=[Depends(get_current_user)]
)


def _parse_json_field(value: str | None) -> dict:
    if not value:
        return {}
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {}


def _config_to_response(c) -> PlatformPublishConfig:
    return PlatformPublishConfig(
        platform=c.platform,
        enabled=c.enabled,
        delay_hours=c.delay_hours,
        pillar_overrides=_parse_json_field(c.pillar_overrides),
    )


@router.get("/publish", response_model=PublishConfigResponse)
async def get_publish_config(repo: ContentRepository = Depends(get_content_repo)):
    """Return auto-publish configuration for all platforms."""
    configs = await repo.get_publish_configs()
    return PublishConfigResponse(platforms=[_config_to_response(c) for c in configs])


@router.put("/publish", response_model=PublishConfigResponse)
async def update_publish_config(
    req: UpdatePublishConfigRequest,
    repo: ContentRepository = Depends(get_content_repo),
):
    """Update auto-publish configuration for one or more platforms."""
    for config in req.platforms:
        data = {
            "enabled": config.enabled,
            "delay_hours": config.delay_hours,
            "pillar_overrides": json.dumps(config.pillar_overrides),
        }
        await repo.upsert_publish_config(platform=config.platform, data=data)

    configs = await repo.get_publish_configs()
    return PublishConfigResponse(platforms=[_config_to_response(c) for c in configs])
