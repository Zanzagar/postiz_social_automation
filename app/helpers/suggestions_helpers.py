"""Testable helpers for the Suggestions page."""


from content_engine.models import Suggestion


def filter_suggestions(
    suggestions: list[Suggestion],
    *,
    pillar_filter: str,
    status_filter: str | None,
) -> list[Suggestion]:
    """Filter suggestions by pillar and/or status.

    Args:
        suggestions: Full list of suggestions.
        pillar_filter: Pillar name to filter by, or "All" for no filter.
        status_filter: Status string to filter by, or None for no filter.
    """
    result = suggestions

    if pillar_filter and pillar_filter != "All":
        result = [s for s in result if s.suggested_pillar.value == pillar_filter]

    if status_filter:
        result = [s for s in result if s.status == status_filter]

    return result


def prepare_accept_data(suggestion: Suggestion) -> dict:
    """Prepare session state data for accepting a suggestion into Create Post."""
    return {
        "prefill_caption": suggestion.content_idea,
        "prefill_pillar": suggestion.suggested_pillar,
        "prefill_date": suggestion.suggested_date,
        "prefill_media_suggestion": suggestion.media_suggestion,
    }
