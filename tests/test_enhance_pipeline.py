"""Tests for the Mode 1 Enhance Pipeline (run_enhance.py)."""

from datetime import datetime
from unittest.mock import MagicMock

from content_engine.models import ContentPillar, ContentRow, ContentStatus, Platform


def _make_row(
    row_number: int = 2,
    raw_text: str = "Baby Lakshmi playing in the meadow today",
    status: ContentStatus = ContentStatus.READY,
    platforms: dict[Platform, bool] | None = None,
    media_url: str | None = None,
) -> ContentRow:
    """Helper to build a ContentRow for testing."""
    if platforms is None:
        platforms = {
            Platform.INSTAGRAM: True,
            Platform.FACEBOOK: True,
            Platform.TIKTOK: False,
            Platform.THREADS: False,
            Platform.LINKEDIN: False,
        }
    return ContentRow(
        row_number=row_number,
        date=datetime(2026, 3, 1),
        content_pillar=ContentPillar.COW_LIFE,
        raw_text=raw_text,
        media_url=media_url,
        platforms=platforms,
        status=status,
        captions={p: None for p in Platform},
    )


# ---------------------------------------------------------------------------
# Import the pipeline function (will fail until implemented — RED phase)
# ---------------------------------------------------------------------------


class TestEnhancePipeline:
    """Test the enhance_pipeline orchestration function."""

    def test_processes_ready_rows(self):
        """Pipeline fetches ready rows, generates captions, creates drafts."""
        from content_engine.pipeline import enhance_pipeline

        row = _make_row()
        sheets = MagicMock()
        sheets.get_rows_by_status.return_value = [row]

        postiz = MagicMock()
        postiz.list_integrations.return_value = [
            {"id": "int-ig", "platform": "instagram"},
            {"id": "int-fb", "platform": "facebook"},
        ]
        postiz.create_draft_post.return_value = {"id": "post-123"}

        generator = MagicMock()
        generator.generate_captions.return_value = {
            Platform.INSTAGRAM: "IG caption",
            Platform.FACEBOOK: "FB caption",
        }

        validator = MagicMock()
        validator.validate_row.return_value = (True, None)

        result = enhance_pipeline(
            sheets=sheets,
            postiz=postiz,
            generator=generator,
            validator=validator,
        )

        sheets.get_rows_by_status.assert_called_once_with(ContentStatus.READY)
        validator.validate_row.assert_called_once_with(row)
        generator.generate_captions.assert_called_once_with(row)
        sheets.update_captions.assert_called_once()
        assert postiz.create_draft_post.call_count == 2  # IG + FB
        sheets.update_status.assert_called_with(row.row_number, ContentStatus.PENDING_APPROVAL)
        assert result.processed == 1
        assert result.errors == 0

    def test_skips_invalid_rows(self):
        """Invalid rows get ERROR status and are skipped."""
        from content_engine.pipeline import enhance_pipeline

        row = _make_row()
        sheets = MagicMock()
        sheets.get_rows_by_status.return_value = [row]

        postiz = MagicMock()
        postiz.list_integrations.return_value = []

        generator = MagicMock()
        validator = MagicMock()
        validator.validate_row.return_value = (False, "Missing raw_text caption")

        result = enhance_pipeline(
            sheets=sheets,
            postiz=postiz,
            generator=generator,
            validator=validator,
        )

        sheets.update_status.assert_called_once_with(
            row.row_number, ContentStatus.ERROR, "Missing raw_text caption"
        )
        generator.generate_captions.assert_not_called()
        postiz.create_draft_post.assert_not_called()
        assert result.processed == 0
        assert result.errors == 1

    def test_continues_after_row_failure(self):
        """If one row fails, other rows are still processed."""
        from content_engine.pipeline import enhance_pipeline

        row_ok = _make_row(row_number=2)
        row_bad = _make_row(row_number=3)

        sheets = MagicMock()
        sheets.get_rows_by_status.return_value = [row_bad, row_ok]

        postiz = MagicMock()
        postiz.list_integrations.return_value = [
            {"id": "int-ig", "platform": "instagram"},
            {"id": "int-fb", "platform": "facebook"},
        ]
        postiz.create_draft_post.return_value = {"id": "post-456"}

        generator = MagicMock()
        # First call raises, second succeeds
        generator.generate_captions.side_effect = [
            RuntimeError("Claude CLI timed out"),
            {Platform.INSTAGRAM: "IG caption", Platform.FACEBOOK: "FB caption"},
        ]

        validator = MagicMock()
        validator.validate_row.return_value = (True, None)

        result = enhance_pipeline(
            sheets=sheets,
            postiz=postiz,
            generator=generator,
            validator=validator,
        )

        assert result.processed == 1
        assert result.errors == 1
        # Bad row gets error status
        sheets.update_status.assert_any_call(
            row_bad.row_number,
            ContentStatus.ERROR,
            "Claude CLI timed out",
        )
        # Good row gets pending_approval
        sheets.update_status.assert_any_call(row_ok.row_number, ContentStatus.PENDING_APPROVAL)

    def test_no_ready_rows(self):
        """Pipeline handles empty queue gracefully."""
        from content_engine.pipeline import enhance_pipeline

        sheets = MagicMock()
        sheets.get_rows_by_status.return_value = []

        postiz = MagicMock()
        postiz.list_integrations.return_value = []

        generator = MagicMock()
        validator = MagicMock()

        result = enhance_pipeline(
            sheets=sheets,
            postiz=postiz,
            generator=generator,
            validator=validator,
        )

        assert result.processed == 0
        assert result.errors == 0
        generator.generate_captions.assert_not_called()

    def test_platform_mapping_filters_unconnected(self):
        """Only platforms connected in Postiz get drafts created."""
        from content_engine.pipeline import enhance_pipeline

        # Row requests IG + FB, but only IG is connected
        row = _make_row()
        sheets = MagicMock()
        sheets.get_rows_by_status.return_value = [row]

        postiz = MagicMock()
        postiz.list_integrations.return_value = [
            {"id": "int-ig", "platform": "instagram"},
            # facebook NOT connected
        ]
        postiz.create_draft_post.return_value = {"id": "post-789"}

        generator = MagicMock()
        generator.generate_captions.return_value = {
            Platform.INSTAGRAM: "IG caption",
            Platform.FACEBOOK: "FB caption",
        }

        validator = MagicMock()
        validator.validate_row.return_value = (True, None)

        result = enhance_pipeline(
            sheets=sheets,
            postiz=postiz,
            generator=generator,
            validator=validator,
        )

        # Only 1 draft (IG), not 2
        assert postiz.create_draft_post.call_count == 1
        call_args = postiz.create_draft_post.call_args
        assert call_args.kwargs["platform_ids"] == ["int-ig"]
        assert result.processed == 1

    def test_postiz_ids_written_to_sheet(self):
        """Postiz draft IDs are recorded back to the Sheet."""
        from content_engine.pipeline import enhance_pipeline

        row = _make_row()
        sheets = MagicMock()
        sheets.get_rows_by_status.return_value = [row]

        postiz = MagicMock()
        postiz.list_integrations.return_value = [
            {"id": "int-ig", "platform": "instagram"},
        ]
        postiz.create_draft_post.return_value = {"id": "draft-abc"}

        generator = MagicMock()
        generator.generate_captions.return_value = {
            Platform.INSTAGRAM: "IG caption",
        }

        validator = MagicMock()
        validator.validate_row.return_value = (True, None)

        enhance_pipeline(
            sheets=sheets,
            postiz=postiz,
            generator=generator,
            validator=validator,
        )

        sheets.update_postiz_ids.assert_called_once_with(row.row_number, "draft-abc")

    def test_multiple_postiz_ids_joined(self):
        """When multiple platforms get drafts, IDs are comma-joined."""
        from content_engine.pipeline import enhance_pipeline

        row = _make_row()
        sheets = MagicMock()
        sheets.get_rows_by_status.return_value = [row]

        postiz = MagicMock()
        postiz.list_integrations.return_value = [
            {"id": "int-ig", "platform": "instagram"},
            {"id": "int-fb", "platform": "facebook"},
        ]
        postiz.create_draft_post.side_effect = [
            {"id": "draft-1"},
            {"id": "draft-2"},
        ]

        generator = MagicMock()
        generator.generate_captions.return_value = {
            Platform.INSTAGRAM: "IG caption",
            Platform.FACEBOOK: "FB caption",
        }

        validator = MagicMock()
        validator.validate_row.return_value = (True, None)

        enhance_pipeline(
            sheets=sheets,
            postiz=postiz,
            generator=generator,
            validator=validator,
        )

        sheets.update_postiz_ids.assert_called_once_with(row.row_number, "draft-1,draft-2")

    def test_postiz_draft_failure_marks_error(self):
        """If Postiz draft creation fails, row gets ERROR status."""
        from content_engine.pipeline import enhance_pipeline

        row = _make_row()
        sheets = MagicMock()
        sheets.get_rows_by_status.return_value = [row]

        postiz = MagicMock()
        postiz.list_integrations.return_value = [
            {"id": "int-ig", "platform": "instagram"},
        ]
        postiz.create_draft_post.side_effect = Exception("API down")

        generator = MagicMock()
        generator.generate_captions.return_value = {
            Platform.INSTAGRAM: "IG caption",
        }

        validator = MagicMock()
        validator.validate_row.return_value = (True, None)

        result = enhance_pipeline(
            sheets=sheets,
            postiz=postiz,
            generator=generator,
            validator=validator,
        )

        sheets.update_status.assert_called_with(row.row_number, ContentStatus.ERROR, "API down")
        assert result.errors == 1

    def test_media_url_passed_to_postiz(self):
        """When row has media_url, it's passed through to Postiz draft."""
        from content_engine.pipeline import enhance_pipeline

        row = _make_row(media_url="https://example.com/cow.jpg")
        sheets = MagicMock()
        sheets.get_rows_by_status.return_value = [row]

        postiz = MagicMock()
        postiz.list_integrations.return_value = [
            {"id": "int-ig", "platform": "instagram"},
        ]
        postiz.create_draft_post.return_value = {"id": "draft-media"}

        generator = MagicMock()
        generator.generate_captions.return_value = {
            Platform.INSTAGRAM: "IG caption",
        }

        validator = MagicMock()
        validator.validate_row.return_value = (True, None)

        enhance_pipeline(
            sheets=sheets,
            postiz=postiz,
            generator=generator,
            validator=validator,
        )

        call_kwargs = postiz.create_draft_post.call_args.kwargs
        assert call_kwargs["media_url"] == "https://example.com/cow.jpg"


class TestPipelineResult:
    """Test the PipelineResult dataclass."""

    def test_result_fields(self):
        from content_engine.pipeline import PipelineResult

        r = PipelineResult(processed=3, errors=1, skipped=2)
        assert r.processed == 3
        assert r.errors == 1
        assert r.skipped == 2

    def test_result_defaults(self):
        from content_engine.pipeline import PipelineResult

        r = PipelineResult()
        assert r.processed == 0
        assert r.errors == 0
        assert r.skipped == 0
