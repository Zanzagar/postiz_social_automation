"""Database connection helpers and seed data for the Gita Valley content database."""

import json
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from api.models import Template

DATABASE_PATH = Path("data/gvsa.db")
DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_PATH}"

_engine_cache: dict[str, object] = {}


def get_async_engine(url: str | None = None):
    """Get or create a cached async SQLAlchemy engine."""
    url = url or DATABASE_URL
    if url not in _engine_cache:
        _engine_cache[url] = create_async_engine(url, echo=False)
    return _engine_cache[url]


async def get_db_session(url: str | None = None) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    engine = get_async_engine(url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


STARTER_TEMPLATES = [
    {
        "name": "Sunday Feast",
        "pillar": "events",
        "platform_instructions": json.dumps(
            {
                "instagram": "Warm, inviting tone. Include feast highlights and community photos.",
                "facebook": "Include full event details: time, location, menu, parking info.",
            }
        ),
        "raw_text_template": "Join us for Sunday Feast at Gita Valley! This week: {{menu}}. "
        "Doors open at {{time}}. All are welcome!",
        "variables": json.dumps(
            [
                {"name": "menu", "type": "text"},
                {"name": "time", "type": "text"},
            ]
        ),
        "schedule_pattern": "weekly:sunday",
    },
    {
        "name": "Weekly Verse",
        "pillar": "spiritual_education",
        "platform_instructions": json.dumps(
            {
                "instagram": "Contemplative tone. Include verse in Sanskrit and English.",
                "facebook": "Add brief commentary on the verse's practical application.",
            }
        ),
        "raw_text_template": "This week's verse: {{verse_ref}} — {{verse_text}}",
        "variables": json.dumps(
            [
                {"name": "verse_ref", "type": "text"},
                {"name": "verse_text", "type": "text"},
            ]
        ),
        "schedule_pattern": "weekly:monday",
    },
    {
        "name": "Farm Update",
        "pillar": "farm_community",
        "platform_instructions": json.dumps(
            {
                "instagram": "Celebrate farm life. Show the beauty of sustainable living.",
                "facebook": "Include updates on crops, animals, and community projects.",
            }
        ),
        "raw_text_template": "Farm update from Gita Valley: {{update}}",
        "variables": json.dumps(
            [
                {"name": "update", "type": "text"},
            ]
        ),
        "schedule_pattern": "weekly:wednesday",
    },
    {
        "name": "Event Promotion",
        "pillar": "events",
        "platform_instructions": json.dumps(
            {
                "instagram": "Eye-catching, exciting tone. Focus on attendee experience.",
                "facebook": "Full details: date, time, location, registration link, what to bring.",
            }
        ),
        "raw_text_template": "{{event_name}} at Gita Valley — {{date}}. {{description}}",
        "variables": json.dumps(
            [
                {"name": "event_name", "type": "text"},
                {"name": "date", "type": "text"},
                {"name": "description", "type": "text"},
            ]
        ),
        "schedule_pattern": None,
    },
]


def seed_starter_templates(session: Session) -> None:
    """Seed the database with starter templates if they don't exist."""
    for tmpl_data in STARTER_TEMPLATES:
        existing = session.query(Template).filter_by(name=tmpl_data["name"]).first()
        if existing is None:
            session.add(Template(**tmpl_data))
    session.commit()
