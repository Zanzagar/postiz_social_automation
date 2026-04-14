"""Settings endpoints: auto-publish config, brand settings, voice rules."""

import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text

from api.auth import get_current_user
from api.dependencies import get_content_repo, get_db
from api.repositories.content import ContentRepository
from api.schemas import (
    BrandSettingsUpdate,
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


# --- Brand Settings ---


@router.get("/brand")
async def get_brand_settings(session=Depends(get_db)):
    """Return all brand settings as a flat dict."""
    try:
        result = await session.execute(text("SELECT key, value FROM brand_settings"))
        rows = result.fetchall()
    except Exception:
        return {}
    return {row[0]: row[1] for row in rows}


@router.put("/brand")
async def update_brand_settings(
    req: BrandSettingsUpdate,
    session=Depends(get_db),
):
    """Update brand settings. Only provided keys are changed."""
    updates = req.model_dump(exclude_unset=True)
    now = datetime.now(UTC).isoformat()
    for key, value in updates.items():
        await session.execute(
            text(
                "INSERT INTO brand_settings (key, value, updated_at) "
                "VALUES (:key, :value, :now) "
                "ON CONFLICT(key) DO UPDATE SET "
                "value = :value, updated_at = :now"
            ),
            {"key": key, "value": str(value), "now": now},
        )
    await session.commit()

    # Return full settings
    result = await session.execute(text("SELECT key, value FROM brand_settings"))
    rows = result.fetchall()
    return {row[0]: row[1] for row in rows}


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


# --- Few-Shot Examples ---


class FewShotCreate(BaseModel):
    platform: str
    pillar: str | None = None
    raw_text: str | None = None
    caption: str
    engagement_score: float = 0.0


@router.get("/few-shot")
async def list_few_shot_examples(session=Depends(get_db)):
    """List all active few-shot examples."""
    try:
        result = await session.execute(
            text(
                "SELECT id, platform, pillar, raw_text, caption, "
                "engagement_score FROM few_shot_examples "
                "WHERE is_active = 1 ORDER BY engagement_score DESC"
            )
        )
        rows = result.fetchall()
    except Exception:
        return []
    return [
        {
            "id": r[0],
            "platform": r[1],
            "pillar": r[2],
            "raw_text": r[3],
            "caption": r[4],
            "engagement_score": r[5],
        }
        for r in rows
    ]


@router.post("/few-shot")
async def create_few_shot_example(req: FewShotCreate, session=Depends(get_db)):
    """Add a new few-shot example."""
    await session.execute(
        text(
            "INSERT INTO few_shot_examples "
            "(platform, pillar, raw_text, caption, engagement_score, "
            "is_active) "
            "VALUES (:platform, :pillar, :raw_text, :caption, :score, 1)"
        ),
        {
            "platform": req.platform,
            "pillar": req.pillar,
            "raw_text": req.raw_text,
            "caption": req.caption,
            "score": req.engagement_score,
        },
    )
    await session.commit()

    # Return the created row
    result = await session.execute(text("SELECT last_insert_rowid()"))
    row_id = result.scalar()
    return {
        "id": row_id,
        "platform": req.platform,
        "pillar": req.pillar,
        "raw_text": req.raw_text,
        "caption": req.caption,
        "engagement_score": req.engagement_score,
    }


@router.delete("/few-shot/{example_id}")
async def delete_few_shot_example(example_id: int, session=Depends(get_db)):
    """Soft-delete a few-shot example."""
    await session.execute(
        text("UPDATE few_shot_examples SET is_active = 0 WHERE id = :id"),
        {"id": example_id},
    )
    await session.commit()
    return {"ok": True}
