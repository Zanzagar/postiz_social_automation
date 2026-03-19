"""Tests for the Mode 2 Suggestion Pipeline (Task 16).

Tests verify:
- Pipeline orchestrates intelligence analysis → AI generation → Sheet writes
- Calendar gaps are converted to date strings for the generator
- Pillar balance is simplified for the generator prompt
- Upcoming events are passed through
- Each suggestion is written to the Sheet
- Errors per-suggestion don't break the pipeline
- PipelineResult counts are accurate
"""

from datetime import datetime
from unittest.mock import MagicMock

from content_engine.models import Suggestion
from content_engine.pipeline import PipelineResult, suggest_pipeline


class TestSuggestPipeline:
    def _make_mocks(self):
        sheets = MagicMock()
        postiz = MagicMock()
        generator = MagicMock()
        intelligence = MagicMock()
        return sheets, postiz, generator, intelligence

    def test_generates_suggestions_from_gaps_and_balance(self) -> None:
        sheets, postiz, generator, intelligence = self._make_mocks()

        intelligence.analyze_calendar_gaps.return_value = [
            {"date": "2026-03-01"},
            {"date": "2026-03-03"},
        ]
        intelligence.analyze_pillar_balance.return_value = {
            "Cow Life": {"actual": 0.30, "target": 0.40, "deviation": -0.10},
            "Farm Ops": {"actual": 0.30, "target": 0.25, "deviation": 0.05},
        }
        intelligence.get_upcoming_events.return_value = []

        suggestion = Suggestion(
            suggested_date=datetime(2026, 3, 1),
            content_idea="Photo of morning milking routine",
            suggested_pillar="Cow Life",
            rationale="Cow Life pillar is underrepresented",
            media_suggestion="Photo of cows in the barn",
        )
        generator.generate_suggestions.return_value = [suggestion]

        result = suggest_pipeline(
            sheets=sheets,
            postiz=postiz,
            generator=generator,
            intelligence=intelligence,
        )

        generator.generate_suggestions.assert_called_once()
        call_args = generator.generate_suggestions.call_args
        assert call_args.kwargs["calendar_gaps"] == ["2026-03-01", "2026-03-03"]
        assert isinstance(result, PipelineResult)
        assert result.processed == 1

    def test_writes_each_suggestion_to_sheet(self) -> None:
        sheets, postiz, generator, intelligence = self._make_mocks()

        intelligence.analyze_calendar_gaps.return_value = [{"date": "2026-03-01"}]
        intelligence.analyze_pillar_balance.return_value = {}
        intelligence.get_upcoming_events.return_value = []

        s1 = Suggestion(
            suggested_date=datetime(2026, 3, 1),
            content_idea="Idea 1",
            suggested_pillar="Cow Life",
            rationale="r1",
            media_suggestion="m1",
        )
        s2 = Suggestion(
            suggested_date=datetime(2026, 3, 2),
            content_idea="Idea 2",
            suggested_pillar="Farm Ops",
            rationale="r2",
            media_suggestion="m2",
        )
        generator.generate_suggestions.return_value = [s1, s2]

        result = suggest_pipeline(
            sheets=sheets,
            postiz=postiz,
            generator=generator,
            intelligence=intelligence,
        )

        assert sheets.add_suggestion.call_count == 2
        sheets.add_suggestion.assert_any_call(s1)
        sheets.add_suggestion.assert_any_call(s2)
        assert result.processed == 2

    def test_continues_after_sheet_write_failure(self) -> None:
        sheets, postiz, generator, intelligence = self._make_mocks()

        intelligence.analyze_calendar_gaps.return_value = []
        intelligence.analyze_pillar_balance.return_value = {}
        intelligence.get_upcoming_events.return_value = []

        s1 = Suggestion(
            suggested_date=datetime(2026, 3, 1),
            content_idea="Idea 1",
            suggested_pillar="Cow Life",
            rationale="r1",
            media_suggestion="m1",
        )
        s2 = Suggestion(
            suggested_date=datetime(2026, 3, 2),
            content_idea="Idea 2",
            suggested_pillar="Farm Ops",
            rationale="r2",
            media_suggestion="m2",
        )
        generator.generate_suggestions.return_value = [s1, s2]

        # First write fails, second succeeds
        sheets.add_suggestion.side_effect = [Exception("Sheet error"), None]

        result = suggest_pipeline(
            sheets=sheets,
            postiz=postiz,
            generator=generator,
            intelligence=intelligence,
        )

        assert result.processed == 1
        assert result.errors == 1

    def test_handles_no_gaps(self) -> None:
        sheets, postiz, generator, intelligence = self._make_mocks()

        intelligence.analyze_calendar_gaps.return_value = []
        intelligence.analyze_pillar_balance.return_value = {}
        intelligence.get_upcoming_events.return_value = []
        generator.generate_suggestions.return_value = []

        result = suggest_pipeline(
            sheets=sheets,
            postiz=postiz,
            generator=generator,
            intelligence=intelligence,
        )

        assert result.processed == 0
        assert result.errors == 0

    def test_simplifies_pillar_balance_for_generator(self) -> None:
        """Generator should receive {'Cow Life': 0.30, ...} not nested dicts."""
        sheets, postiz, generator, intelligence = self._make_mocks()

        intelligence.analyze_calendar_gaps.return_value = [{"date": "2026-03-01"}]
        intelligence.analyze_pillar_balance.return_value = {
            "Cow Life": {"actual": 0.30, "target": 0.40, "deviation": -0.10},
        }
        intelligence.get_upcoming_events.return_value = []
        generator.generate_suggestions.return_value = []

        suggest_pipeline(
            sheets=sheets,
            postiz=postiz,
            generator=generator,
            intelligence=intelligence,
        )

        call_kwargs = generator.generate_suggestions.call_args.kwargs
        balance = call_kwargs["pillar_balance"]
        # Should be simplified: pillar_name -> actual_pct
        assert balance == {"Cow Life": 0.30}

    def test_logs_error_on_generation_failure(self) -> None:
        sheets, postiz, generator, intelligence = self._make_mocks()

        intelligence.analyze_calendar_gaps.return_value = [{"date": "2026-03-01"}]
        intelligence.analyze_pillar_balance.return_value = {}
        intelligence.get_upcoming_events.return_value = []
        generator.generate_suggestions.side_effect = RuntimeError("Claude CLI failed")

        result = suggest_pipeline(
            sheets=sheets,
            postiz=postiz,
            generator=generator,
            intelligence=intelligence,
        )

        assert result.errors == 1
        assert result.processed == 0
        sheets.log_error.assert_called_once()


class TestRunSuggestScript:
    def test_main_is_callable(self) -> None:
        from content_engine.scripts.run_suggest import main

        assert callable(main)
