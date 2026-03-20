"""Integration tests — verify full pipeline flows with mocked externals (Task 25).

Tests exercise the pipeline functions end-to-end with mock SheetsClient,
PostizClient, CaptionGenerator, and ContentIntelligence.
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from content_engine.models import (
    ContentRow,
    ContentStatus,
    Platform,
    PostPerformance,
    Suggestion,
)
from content_engine.pipeline import (
    enhance_pipeline,
    learn_pipeline,
    suggest_pipeline,
)
from content_engine.validator import ContentValidator

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_row(**overrides) -> ContentRow:
    defaults = {
        "row_number": 2,
        "date": datetime(2026, 3, 1),
        "content_pillar": "Cow Life",
        "raw_text": "Lakshmi enjoying the morning sun",
        "media_url": None,
        "platforms": {Platform.INSTAGRAM: True, Platform.FACEBOOK: True},
        "status": ContentStatus.READY,
        "captions": {},
    }
    defaults.update(overrides)
    return ContentRow(**defaults)


@pytest.fixture
def mock_sheets() -> MagicMock:
    sheets = MagicMock()
    sheets.get_rows_by_status.return_value = []
    sheets.get_rows_with_feedback.return_value = []
    sheets.get_all_content_rows.return_value = []
    sheets.get_suggestions.return_value = []
    sheets.get_recent_errors.return_value = []
    return sheets


@pytest.fixture
def mock_postiz() -> MagicMock:
    postiz = MagicMock()
    postiz.list_integrations.return_value = [
        {"platform": "instagram", "id": "ig-1"},
        {"platform": "facebook", "id": "fb-1"},
    ]
    postiz.create_draft_post.return_value = {"id": "draft-123"}
    return postiz


@pytest.fixture
def mock_generator() -> MagicMock:
    gen = MagicMock()
    gen.generate_captions.return_value = {
        Platform.INSTAGRAM: "IG caption text",
        Platform.FACEBOOK: "FB caption text",
    }
    gen.generate_suggestions.return_value = [
        Suggestion(
            suggested_date=datetime(2026, 3, 5),
            content_idea="Photo of new calves",
            suggested_pillar="Cow Life",
            rationale="Cow Life underrepresented",
            media_suggestion="Photo of calves",
        )
    ]
    return gen


@pytest.fixture
def mock_intelligence() -> MagicMock:
    intel = MagicMock()
    intel.analyze_calendar_gaps.return_value = [
        {"date": "2026-03-05"},
        {"date": "2026-03-06"},
    ]
    intel.analyze_pillar_balance.return_value = {
        "Cow Life": {"actual": 0.15, "target": 0.25},
        "Farm Ops": {"actual": 0.30, "target": 0.25},
    }
    intel.get_upcoming_events.return_value = []
    return intel


# ---------------------------------------------------------------------------
# TestEnhancePipeline
# ---------------------------------------------------------------------------


class TestEnhancePipelineIntegration:
    """Full enhance pipeline flow."""

    def test_success_processes_ready_rows(
        self, mock_sheets: MagicMock, mock_postiz: MagicMock, mock_generator: MagicMock
    ) -> None:
        row = _make_row()
        mock_sheets.get_rows_by_status.return_value = [row]

        result = enhance_pipeline(
            sheets=mock_sheets,
            postiz=mock_postiz,
            generator=mock_generator,
            validator=ContentValidator(),
        )

        assert result.processed == 1
        assert result.errors == 0
        mock_generator.generate_captions.assert_called_once_with(row)
        mock_sheets.update_captions.assert_called_once()
        assert mock_postiz.create_draft_post.call_count == 2  # IG + FB
        mock_sheets.update_status.assert_called_with(2, ContentStatus.PENDING_APPROVAL)

    def test_invalid_row_marked_error(
        self, mock_sheets: MagicMock, mock_postiz: MagicMock, mock_generator: MagicMock
    ) -> None:
        row = _make_row(raw_text="", platforms={})  # invalid: no text, no platforms
        mock_sheets.get_rows_by_status.return_value = [row]

        result = enhance_pipeline(
            sheets=mock_sheets,
            postiz=mock_postiz,
            generator=mock_generator,
            validator=ContentValidator(),
        )

        assert result.errors == 1
        assert result.processed == 0
        mock_sheets.update_status.assert_called_once()
        call_args = mock_sheets.update_status.call_args
        assert call_args[0][1] == ContentStatus.ERROR

    def test_generator_failure_marks_error(
        self, mock_sheets: MagicMock, mock_postiz: MagicMock, mock_generator: MagicMock
    ) -> None:
        row = _make_row()
        mock_sheets.get_rows_by_status.return_value = [row]
        mock_generator.generate_captions.side_effect = RuntimeError("Claude CLI failed")

        result = enhance_pipeline(
            sheets=mock_sheets,
            postiz=mock_postiz,
            generator=mock_generator,
            validator=ContentValidator(),
        )

        assert result.errors == 1
        assert result.processed == 0

    def test_multiple_rows_partial_failure(
        self, mock_sheets: MagicMock, mock_postiz: MagicMock, mock_generator: MagicMock
    ) -> None:
        good_row = _make_row(row_number=2)
        bad_row = _make_row(row_number=3)
        mock_sheets.get_rows_by_status.return_value = [good_row, bad_row]

        # First call succeeds, second fails
        mock_generator.generate_captions.side_effect = [
            {Platform.INSTAGRAM: "Good caption"},
            RuntimeError("Failed"),
        ]

        result = enhance_pipeline(
            sheets=mock_sheets,
            postiz=mock_postiz,
            generator=mock_generator,
            validator=ContentValidator(),
        )

        assert result.processed == 1
        assert result.errors == 1

    def test_no_ready_rows(
        self, mock_sheets: MagicMock, mock_postiz: MagicMock, mock_generator: MagicMock
    ) -> None:
        mock_sheets.get_rows_by_status.return_value = []

        result = enhance_pipeline(
            sheets=mock_sheets,
            postiz=mock_postiz,
            generator=mock_generator,
            validator=ContentValidator(),
        )

        assert result.processed == 0
        assert result.errors == 0
        mock_generator.generate_captions.assert_not_called()


# ---------------------------------------------------------------------------
# TestSuggestPipeline
# ---------------------------------------------------------------------------


class TestSuggestPipelineIntegration:
    """Full suggest pipeline flow."""

    def test_generates_and_writes_suggestions(
        self,
        mock_sheets: MagicMock,
        mock_postiz: MagicMock,
        mock_generator: MagicMock,
        mock_intelligence: MagicMock,
    ) -> None:
        result = suggest_pipeline(
            sheets=mock_sheets,
            postiz=mock_postiz,
            generator=mock_generator,
            intelligence=mock_intelligence,
        )

        assert result.processed == 1
        assert result.errors == 0
        mock_intelligence.analyze_calendar_gaps.assert_called_once()
        mock_intelligence.analyze_pillar_balance.assert_called_once()
        mock_generator.generate_suggestions.assert_called_once()
        mock_sheets.add_suggestion.assert_called_once()

    def test_intelligence_failure_logs_error(
        self,
        mock_sheets: MagicMock,
        mock_postiz: MagicMock,
        mock_generator: MagicMock,
        mock_intelligence: MagicMock,
    ) -> None:
        mock_intelligence.analyze_calendar_gaps.side_effect = RuntimeError("Sheet API down")

        result = suggest_pipeline(
            sheets=mock_sheets,
            postiz=mock_postiz,
            generator=mock_generator,
            intelligence=mock_intelligence,
        )

        assert result.errors == 1
        assert result.processed == 0
        mock_sheets.log_error.assert_called_once()

    def test_no_gaps_still_succeeds(
        self,
        mock_sheets: MagicMock,
        mock_postiz: MagicMock,
        mock_generator: MagicMock,
        mock_intelligence: MagicMock,
    ) -> None:
        mock_intelligence.analyze_calendar_gaps.return_value = []
        mock_generator.generate_suggestions.return_value = []

        result = suggest_pipeline(
            sheets=mock_sheets,
            postiz=mock_postiz,
            generator=mock_generator,
            intelligence=mock_intelligence,
        )

        assert result.errors == 0
        assert result.processed == 0


# ---------------------------------------------------------------------------
# TestLearnPipeline
# ---------------------------------------------------------------------------


class TestLearnPipelineIntegration:
    """Full learn pipeline flow."""

    def test_pulls_analytics_and_saves(
        self,
        mock_sheets: MagicMock,
        mock_postiz: MagicMock,
        mock_intelligence: MagicMock,
        tmp_path: Path,
    ) -> None:
        posted_row = _make_row(
            status=ContentStatus.POSTED,
            postiz_ids="post-1,post-2",
        )
        mock_sheets.get_rows_by_status.return_value = [posted_row]
        mock_postiz.get_post_analytics.return_value = PostPerformance(
            post_id="post-1",
            platform=Platform.INSTAGRAM,
            pillar="Cow Life",
            posted_at=datetime(2026, 3, 1),
            likes=42,
            comments=5,
            shares=3,
            reach=1200,
            engagement_rate=4.2,
        )

        result = learn_pipeline(
            sheets=mock_sheets,
            postiz=mock_postiz,
            intelligence=mock_intelligence,
            data_dir=tmp_path,
        )

        assert result.processed == 2  # post-1 and post-2
        assert result.errors == 0
        perf_path = tmp_path / "post-performance.json"
        assert perf_path.exists()
        data = json.loads(perf_path.read_text())
        assert len(data) == 2
        mock_intelligence.save_learning_context.assert_called_once()

    def test_skips_already_collected_ids(
        self,
        mock_sheets: MagicMock,
        mock_postiz: MagicMock,
        mock_intelligence: MagicMock,
        tmp_path: Path,
    ) -> None:
        # Pre-existing data
        existing = [{"post_id": "post-1", "platform": "instagram"}]
        (tmp_path / "post-performance.json").write_text(json.dumps(existing))

        posted_row = _make_row(
            status=ContentStatus.POSTED,
            postiz_ids="post-1",
        )
        mock_sheets.get_rows_by_status.return_value = [posted_row]

        result = learn_pipeline(
            sheets=mock_sheets,
            postiz=mock_postiz,
            intelligence=mock_intelligence,
            data_dir=tmp_path,
        )

        assert result.skipped == 1
        assert result.processed == 0
        mock_postiz.get_post_analytics.assert_not_called()

    def test_no_posted_rows(
        self,
        mock_sheets: MagicMock,
        mock_postiz: MagicMock,
        mock_intelligence: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_sheets.get_rows_by_status.return_value = []

        result = learn_pipeline(
            sheets=mock_sheets,
            postiz=mock_postiz,
            intelligence=mock_intelligence,
            data_dir=tmp_path,
        )

        assert result.processed == 0
        assert result.errors == 0
        mock_intelligence.save_learning_context.assert_called_once()


# ---------------------------------------------------------------------------
# Cross-pipeline tests
# ---------------------------------------------------------------------------


class TestCrossPipelineIntegration:
    """Tests that verify interactions between pipeline stages."""

    def test_enhance_then_learn_flow(
        self,
        mock_sheets: MagicMock,
        mock_postiz: MagicMock,
        mock_generator: MagicMock,
        mock_intelligence: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Simulate enhance → approve → learn flow."""
        # Step 1: Enhance processes a row
        row = _make_row()
        mock_sheets.get_rows_by_status.return_value = [row]

        enhance_result = enhance_pipeline(
            sheets=mock_sheets,
            postiz=mock_postiz,
            generator=mock_generator,
            validator=ContentValidator(),
        )
        assert enhance_result.processed == 1

        # Step 2: Learn pulls analytics (posted rows)
        posted_row = _make_row(
            status=ContentStatus.POSTED,
            postiz_ids="draft-123",
        )
        mock_sheets.get_rows_by_status.return_value = [posted_row]
        mock_postiz.get_post_analytics.return_value = PostPerformance(
            post_id="draft-123",
            platform=Platform.INSTAGRAM,
            pillar="Cow Life",
            posted_at=datetime(2026, 3, 1),
            likes=100,
        )

        learn_result = learn_pipeline(
            sheets=mock_sheets,
            postiz=mock_postiz,
            intelligence=mock_intelligence,
            data_dir=tmp_path,
        )
        assert learn_result.processed == 1
