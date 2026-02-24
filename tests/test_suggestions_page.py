"""Tests for the Suggestions page (Task 12).

Tests verify:
- Page file exists
- Suggestion filtering by pillar and status
- Accept transfers suggestion data to session state
- Helpers are importable and testable
"""

from datetime import datetime
from pathlib import Path

from content_engine.models import ContentPillar, Suggestion


class TestSuggestionsPageExists:
    def test_page_file_exists(self) -> None:
        page = Path("app/pages/5_Suggestions.py")
        assert page.exists(), f"Suggestions page not found at {page}"


class TestFilterSuggestions:
    """Test the helper that filters suggestions by pillar and status."""

    def _make_suggestions(self) -> list[Suggestion]:
        return [
            Suggestion(
                suggested_date=datetime(2026, 3, 1),
                content_idea="Morning milking photo",
                suggested_pillar=ContentPillar.COW_LIFE,
                rationale="Cow Life underrepresented",
                media_suggestion="Photo of cows",
                status="suggested",
            ),
            Suggestion(
                suggested_date=datetime(2026, 3, 2),
                content_idea="Farm tour video",
                suggested_pillar=ContentPillar.FARM_OPS,
                rationale="Engage visitors",
                media_suggestion="Short reel",
                status="suggested",
            ),
            Suggestion(
                suggested_date=datetime(2026, 3, 3),
                content_idea="Community potluck",
                suggested_pillar=ContentPillar.COMMUNITY,
                rationale="Build engagement",
                media_suggestion="Group photo",
                status="accepted",
            ),
        ]

    def test_filter_by_all_pillars_returns_all(self) -> None:
        from app.pages.suggestions_helpers import filter_suggestions

        suggestions = self._make_suggestions()
        result = filter_suggestions(suggestions, pillar_filter="All", status_filter=None)
        assert len(result) == 3

    def test_filter_by_specific_pillar(self) -> None:
        from app.pages.suggestions_helpers import filter_suggestions

        suggestions = self._make_suggestions()
        result = filter_suggestions(suggestions, pillar_filter="Cow Life", status_filter=None)
        assert len(result) == 1
        assert result[0].suggested_pillar == ContentPillar.COW_LIFE

    def test_filter_by_status(self) -> None:
        from app.pages.suggestions_helpers import filter_suggestions

        suggestions = self._make_suggestions()
        result = filter_suggestions(suggestions, pillar_filter="All", status_filter="accepted")
        assert len(result) == 1
        assert result[0].status == "accepted"

    def test_filter_by_pillar_and_status(self) -> None:
        from app.pages.suggestions_helpers import filter_suggestions

        suggestions = self._make_suggestions()
        result = filter_suggestions(
            suggestions, pillar_filter="Community", status_filter="accepted"
        )
        assert len(result) == 1
        assert result[0].suggested_pillar == ContentPillar.COMMUNITY

    def test_filter_returns_empty_when_no_match(self) -> None:
        from app.pages.suggestions_helpers import filter_suggestions

        suggestions = self._make_suggestions()
        result = filter_suggestions(suggestions, pillar_filter="Kitchen", status_filter="suggested")
        assert len(result) == 0


class TestPrepareAcceptData:
    """Test helper that prepares session state data when accepting a suggestion."""

    def test_returns_prefill_dict(self) -> None:
        from app.pages.suggestions_helpers import prepare_accept_data

        suggestion = Suggestion(
            suggested_date=datetime(2026, 3, 1),
            content_idea="Morning milking photo",
            suggested_pillar=ContentPillar.COW_LIFE,
            rationale="Cow Life underrepresented",
            media_suggestion="Photo of cows",
        )
        data = prepare_accept_data(suggestion)
        assert data["prefill_caption"] == "Morning milking photo"
        assert data["prefill_pillar"] == ContentPillar.COW_LIFE
        assert data["prefill_date"] == datetime(2026, 3, 1)
        assert data["prefill_media_suggestion"] == "Photo of cows"
