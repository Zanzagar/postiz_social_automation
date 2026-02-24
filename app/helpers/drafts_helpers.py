"""Testable helpers for the Drafts Review page."""

from content_engine.models import ContentRow, Platform


def get_enabled_platforms(row: ContentRow) -> list[Platform]:
    """Return only the platforms that are enabled (True) for this row."""
    return [p for p, enabled in row.platforms.items() if enabled]


def get_caption_for_platform(row: ContentRow, platform: Platform) -> str:
    """Get the caption text for a platform, returning empty string if missing/None."""
    caption = row.captions.get(platform)
    return caption if caption else ""


def build_postiz_link(
    postiz_ids: str | None,
    base_url: str = "https://postiz.sethpc.xyz",
) -> str | None:
    """Construct a Postiz URL from post IDs. Returns None if no IDs."""
    if not postiz_ids:
        return None
    return f"{base_url}/posts/{postiz_ids}"


def prepare_batch_approve(drafts: list[ContentRow]) -> list[dict]:
    """Prepare data for batch approval of multiple drafts.

    Returns a list of dicts with row_number and enabled_platforms for each draft.
    """
    return [
        {
            "row_number": draft.row_number,
            "raw_text": draft.raw_text,
            "enabled_platforms": get_enabled_platforms(draft),
            "captions": draft.captions,
        }
        for draft in drafts
    ]


def apply_caption_edits(row: ContentRow, edits: dict[Platform, str]) -> ContentRow:
    """Apply inline caption edits, returning a new ContentRow instance."""
    updated_captions = dict(row.captions)
    for platform, new_text in edits.items():
        updated_captions[platform] = new_text
    return row.model_copy(update={"captions": updated_captions})
