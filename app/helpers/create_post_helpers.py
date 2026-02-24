"""Testable helpers for the Create Post page.

All business logic is extracted here so it can be tested without Streamlit.
The Streamlit page (1_Create_Review.py) calls these functions.
"""

import logging
from datetime import datetime

from content_engine.generator import CaptionGenerator
from content_engine.models import ContentRow, ContentStatus, Platform
from content_engine.postiz import PostizClient

logger = logging.getLogger(__name__)


def build_content_row(
    *,
    caption: str,
    media_url: str,
    platforms: dict[Platform, bool],
    scheduled_date: datetime,
) -> ContentRow:
    """Convert form inputs into a ContentRow for the generator."""
    return ContentRow(
        row_number=0,
        date=scheduled_date
        if isinstance(scheduled_date, datetime)
        else datetime.combine(scheduled_date, datetime.min.time()),
        raw_text=caption,
        media_url=media_url if media_url else None,
        platforms=platforms,
        status=ContentStatus.DRAFT,
        captions={},
    )


def generate_captions(
    *,
    generator: CaptionGenerator,
    row: ContentRow,
) -> dict[Platform, str]:
    """Generate AI captions for all enabled platforms."""
    return generator.generate_captions(row)


def regenerate_with_feedback(
    *,
    generator: CaptionGenerator,
    row: ContentRow,
    feedback: str,
) -> dict[Platform, str]:
    """Regenerate captions incorporating staff feedback."""
    return generator.generate_captions(row, feedback=feedback)


def send_to_postiz(
    *,
    postiz: PostizClient,
    captions: dict[Platform, str],
    media_url: str | None,
    scheduled_at: str | None,
) -> list[str]:
    """Create draft posts in Postiz for each connected platform.

    Returns list of Postiz draft IDs.
    """
    integrations = postiz.list_integrations()
    platform_map: dict[str, str] = {i["platform"]: i["id"] for i in integrations}

    draft_ids: list[str] = []
    for platform, caption_text in captions.items():
        platform_key = platform.value
        if platform_key not in platform_map:
            logger.info("Skipping %s — not connected in Postiz", platform_key)
            continue

        draft = postiz.create_draft_post(
            content=caption_text,
            platform_ids=[platform_map[platform_key]],
            media_url=media_url,
            scheduled_at=scheduled_at,
        )
        draft_ids.append(draft["id"])
        logger.info("Created Postiz draft for %s: %s", platform_key, draft["id"])

    return draft_ids
