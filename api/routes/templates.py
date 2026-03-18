"""Content templates CRUD and generation endpoints."""

import asyncio
import json
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from api.auth import get_current_user
from api.dependencies import get_caption_generator, get_content_repo
from api.repositories.content import ContentRepository
from api.routes.content import _row_to_response
from api.schemas import (
    GenerateFromTemplateRequest,
    TemplateCreateRequest,
    TemplateResponse,
    TemplateVariable,
)
from content_engine.models import ContentRow as EngineContentRow
from content_engine.models import ContentStatus, Platform

router = APIRouter(
    prefix="/api/templates", tags=["templates"], dependencies=[Depends(get_current_user)]
)


def _parse_json_field(value: str | None) -> dict | list:
    if not value:
        return {}
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {}


def _template_to_response(t) -> TemplateResponse:
    platform_instructions = _parse_json_field(t.platform_instructions)
    variables_raw = _parse_json_field(t.variables)
    variables = (
        [TemplateVariable(**v) for v in variables_raw] if isinstance(variables_raw, list) else []
    )

    return TemplateResponse(
        id=t.id,
        name=t.name,
        pillar=t.pillar,
        platform_instructions=platform_instructions
        if isinstance(platform_instructions, dict)
        else {},
        raw_text_template=t.raw_text_template,
        variables=variables,
        schedule_pattern=t.schedule_pattern,
        default_segment_id=t.default_segment_id,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


@router.get("", response_model=list[TemplateResponse])
async def list_templates(repo: ContentRepository = Depends(get_content_repo)):
    templates = await repo.get_templates()
    return [_template_to_response(t) for t in templates]


@router.post("", response_model=TemplateResponse)
async def create_template(
    req: TemplateCreateRequest,
    repo: ContentRepository = Depends(get_content_repo),
):
    template = await repo.create_template(
        {
            "name": req.name,
            "pillar": req.pillar,
            "platform_instructions": json.dumps(req.platform_instructions),
            "raw_text_template": req.raw_text_template,
            "variables": json.dumps([v.model_dump() for v in req.variables]),
            "schedule_pattern": req.schedule_pattern,
            "default_segment_id": req.default_segment_id,
        }
    )
    return _template_to_response(template)


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: int,
    repo: ContentRepository = Depends(get_content_repo),
):
    template = await repo.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return _template_to_response(template)


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: int,
    req: TemplateCreateRequest,
    repo: ContentRepository = Depends(get_content_repo),
):
    data = {
        "name": req.name,
        "pillar": req.pillar,
        "platform_instructions": json.dumps(req.platform_instructions),
        "raw_text_template": req.raw_text_template,
        "variables": json.dumps([v.model_dump() for v in req.variables]),
        "schedule_pattern": req.schedule_pattern,
        "default_segment_id": req.default_segment_id,
    }
    template = await repo.update_template(template_id, data)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return _template_to_response(template)


@router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    repo: ContentRepository = Depends(get_content_repo),
):
    await repo.delete_template(template_id)
    return {"deleted": True}


@router.post("/{template_id}/generate")
async def generate_from_template(
    template_id: int,
    req: GenerateFromTemplateRequest,
    repo: ContentRepository = Depends(get_content_repo),
    generator=Depends(get_caption_generator),
):
    """Substitute variables, create content row, and generate captions."""
    template = await repo.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Variable substitution
    raw_text = template.raw_text_template or ""
    for var_name, var_value in req.variable_values.items():
        raw_text = raw_text.replace(f"{{{{{var_name}}}}}", var_value)

    # Verify all variables substituted
    remaining = re.findall(r"\{\{(\w+)\}\}", raw_text)
    if remaining:
        raise HTTPException(status_code=400, detail=f"Missing variables: {remaining}")

    # Create content row
    platforms_json = json.dumps({p: True for p in req.platforms})
    content_row = await repo.create_content_row(
        {
            "date": datetime.fromisoformat(req.scheduled_date),
            "pillar": template.pillar,
            "raw_text": raw_text,
            "platforms": platforms_json,
            "status": "draft",
            "captions": "{}",
            "source": "template",
            "template_id": template_id,
        }
    )

    # Generate captions
    engine_row = EngineContentRow(
        row_number=content_row.id,
        date=content_row.date or datetime.now(),
        raw_text=raw_text,
        platforms={Platform(p): True for p in req.platforms},
        status=ContentStatus.DRAFT,
        captions={},
    )
    captions = await asyncio.to_thread(generator.generate_captions, engine_row)
    captions_json = json.dumps({str(k): v for k, v in captions.items()})
    await repo.update_captions(content_row.id, captions_json)

    updated = await repo.get_content_row(content_row.id)
    return _row_to_response(updated)
