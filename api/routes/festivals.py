"""ISKCON festival calendar API endpoints."""

import json
from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from api.auth import get_current_user

router = APIRouter(prefix="/api", tags=["festivals"], dependencies=[Depends(get_current_user)])

CALENDAR_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "iskcon_calendar.json"


class FestivalResponse(BaseModel):
    name: str
    date: str
    significance: str
    suggested_content_angles: list[str]
    topic: str
    content_pillar: str


def _load_festivals() -> list[dict]:
    """Load festival data from JSON file."""
    if not CALENDAR_PATH.exists():
        return []
    with open(CALENDAR_PATH) as f:
        return json.load(f)


@router.get("/festivals", response_model=list[FestivalResponse])
async def list_festivals(
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
):
    """Return ISKCON festivals, optionally filtered by date range."""
    festivals = _load_festivals()

    if from_date or to_date:
        filtered = []
        for fest in festivals:
            fest_date = datetime.strptime(fest["date"], "%Y-%m-%d").date()
            if from_date and fest_date < from_date:
                continue
            if to_date and fest_date > to_date:
                continue
            filtered.append(fest)
        festivals = filtered

    return [FestivalResponse(**f) for f in festivals]
