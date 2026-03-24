"""Settings endpoints: auto-publish config, voice rules."""

import json
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.auth import get_current_user
from api.dependencies import get_content_repo
from api.repositories.content import ContentRepository
from api.schemas import (
    PlatformPublishConfig,
    PublishConfigResponse,
    UpdatePublishConfigRequest,
)

_RULES_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "learned-rules.json"

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


# --- Voice Rules ---


class VoiceRulesResponse(BaseModel):
    rules: list[str]
    summary: str


class VoiceRulesUpdate(BaseModel):
    rules: list[str]


def _load_rules() -> dict:
    if _RULES_PATH.exists():
        return json.loads(_RULES_PATH.read_text())
    return {"rules": [], "summary": ""}


@router.get("/voice-rules", response_model=VoiceRulesResponse)
async def get_voice_rules():
    """Return current voice rules."""
    data = _load_rules()
    return VoiceRulesResponse(rules=data.get("rules", []), summary=data.get("summary", ""))


@router.put("/voice-rules", response_model=VoiceRulesResponse)
async def update_voice_rules(req: VoiceRulesUpdate):
    """Replace all voice rules."""
    data = {"rules": req.rules, "summary": "User-defined rules"}
    _RULES_PATH.write_text(json.dumps(data, indent=2))
    return VoiceRulesResponse(**data)


@router.post("/voice-rules")
async def add_voice_rule(rule: str):
    """Add a single voice rule."""
    data = _load_rules()
    data["rules"].append(rule)
    _RULES_PATH.write_text(json.dumps(data, indent=2))
    return {"ok": True, "count": len(data["rules"])}


@router.delete("/voice-rules/{index}")
async def delete_voice_rule(index: int):
    """Delete a voice rule by index."""
    data = _load_rules()
    rules = data.get("rules", [])
    if 0 <= index < len(rules):
        rules.pop(index)
        data["rules"] = rules
        _RULES_PATH.write_text(json.dumps(data, indent=2))
    return {"ok": True, "count": len(rules)}
