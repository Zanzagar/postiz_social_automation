"""Tests for the Create Post page (Task 11).

Tests verify:
- Page file exists with correct naming
- Form inputs: caption, media URL, platform checkboxes, date
- AI generation calls CaptionGenerator correctly
- Generated captions display in editable cards
- Re-prompt passes feedback to generator
- Send to Postiz creates draft posts
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from content_engine.models import ContentRow, ContentStatus, Platform

# ---------------------------------------------------------------------------
# Page structure
# ---------------------------------------------------------------------------


class TestCreatePostPageExists:
    def test_page_file_exists(self) -> None:
        page = Path("app/pages/1_Create_Review.py")
        assert page.exists(), f"Create Post page not found at {page}"


# ---------------------------------------------------------------------------
# Helper: build_content_row (extracted from page for testability)
# ---------------------------------------------------------------------------


class TestBuildContentRow:
    """Test the helper that converts form inputs into a ContentRow."""

    def test_builds_row_with_all_platforms(self) -> None:
        from app.helpers.create_post_helpers import build_content_row

        row = build_content_row(
            caption="Lakshmi loves the morning sun",
            media_url="",
            platforms={Platform.INSTAGRAM: True, Platform.FACEBOOK: True},
            scheduled_date=datetime(2026, 3, 1),
        )
        assert isinstance(row, ContentRow)
        assert row.raw_text == "Lakshmi loves the morning sun"
        assert row.platforms[Platform.INSTAGRAM] is True
        assert row.platforms[Platform.FACEBOOK] is True
        assert row.status == ContentStatus.DRAFT

    def test_builds_row_with_no_media(self) -> None:
        from app.helpers.create_post_helpers import build_content_row

        row = build_content_row(
            caption="Test",
            media_url="",
            platforms={Platform.INSTAGRAM: True},
            scheduled_date=datetime(2026, 3, 1),
        )
        assert row.media_url is None

    def test_builds_row_with_media_url(self) -> None:
        from app.helpers.create_post_helpers import build_content_row

        row = build_content_row(
            caption="Test",
            media_url="https://drive.google.com/file/d/abc123/view",
            platforms={Platform.INSTAGRAM: True},
            scheduled_date=datetime(2026, 3, 1),
        )
        assert row.media_url is not None
        assert "abc123" in str(row.media_url)

    def test_defaults_all_platforms_false_when_none_selected(self) -> None:
        from app.helpers.create_post_helpers import build_content_row

        row = build_content_row(
            caption="Test",
            media_url="",
            platforms={},
            scheduled_date=datetime(2026, 3, 1),
        )
        assert row.platforms == {}

    def test_sets_date_correctly(self) -> None:
        from app.helpers.create_post_helpers import build_content_row

        target = datetime(2026, 4, 15)
        row = build_content_row(
            caption="Test",
            media_url="",
            platforms={Platform.INSTAGRAM: True},
            scheduled_date=target,
        )
        assert row.date.year == 2026
        assert row.date.month == 4
        assert row.date.day == 15


# ---------------------------------------------------------------------------
# Caption generation
# ---------------------------------------------------------------------------


class TestGenerateCaptions:
    def test_generator_called_with_content_row(self) -> None:
        """CaptionGenerator.generate_captions receives the built ContentRow."""
        from app.helpers.create_post_helpers import generate_captions

        mock_gen = MagicMock()
        mock_gen.generate_captions.return_value = {
            Platform.INSTAGRAM: "IG caption",
            Platform.FACEBOOK: "FB caption",
        }
        row = ContentRow(
            row_number=0,
            date=datetime(2026, 3, 1),
            raw_text="Test",
            platforms={Platform.INSTAGRAM: True, Platform.FACEBOOK: True},
            status=ContentStatus.DRAFT,
            captions={},
        )
        result = generate_captions(generator=mock_gen, row=row)
        mock_gen.generate_captions.assert_called_once_with(row)
        assert Platform.INSTAGRAM in result
        assert result[Platform.INSTAGRAM] == "IG caption"

    def test_generator_returns_empty_when_no_platforms(self) -> None:
        from app.helpers.create_post_helpers import generate_captions

        mock_gen = MagicMock()
        mock_gen.generate_captions.return_value = {}
        row = ContentRow(
            row_number=0,
            date=datetime(2026, 3, 1),
            raw_text="Test",
            platforms={},
            status=ContentStatus.DRAFT,
            captions={},
        )
        result = generate_captions(generator=mock_gen, row=row)
        assert result == {}


# ---------------------------------------------------------------------------
# Re-prompt
# ---------------------------------------------------------------------------


class TestReprompt:
    def test_reprompt_passes_feedback_to_generator(self) -> None:
        from app.helpers.create_post_helpers import regenerate_with_feedback

        mock_gen = MagicMock()
        mock_gen.generate_captions.return_value = {Platform.INSTAGRAM: "Updated IG"}
        row = ContentRow(
            row_number=0,
            date=datetime(2026, 3, 1),
            raw_text="Test",
            platforms={Platform.INSTAGRAM: True},
            status=ContentStatus.DRAFT,
            captions={},
        )
        result = regenerate_with_feedback(generator=mock_gen, row=row, feedback="Make it funnier")
        mock_gen.generate_captions.assert_called_once_with(row, feedback="Make it funnier")
        assert result[Platform.INSTAGRAM] == "Updated IG"


# ---------------------------------------------------------------------------
# Send to Postiz
# ---------------------------------------------------------------------------


class TestSendToPostiz:
    def test_creates_draft_for_each_platform(self) -> None:
        from app.helpers.create_post_helpers import send_to_postiz

        mock_postiz = MagicMock()
        mock_postiz.list_integrations.return_value = [
            {"id": "int_ig", "platform": "instagram"},
            {"id": "int_fb", "platform": "facebook"},
        ]
        mock_postiz.create_draft_post.return_value = {"id": "draft_1"}

        captions = {
            Platform.INSTAGRAM: "IG caption",
            Platform.FACEBOOK: "FB caption",
        }
        draft_ids = send_to_postiz(
            postiz=mock_postiz,
            captions=captions,
            media_url=None,
            scheduled_at=None,
        )
        assert len(draft_ids) == 2
        assert mock_postiz.create_draft_post.call_count == 2

    def test_skips_platform_not_connected(self) -> None:
        from app.helpers.create_post_helpers import send_to_postiz

        mock_postiz = MagicMock()
        mock_postiz.list_integrations.return_value = [
            {"id": "int_ig", "platform": "instagram"},
        ]
        mock_postiz.create_draft_post.return_value = {"id": "draft_1"}

        captions = {
            Platform.INSTAGRAM: "IG caption",
            Platform.TIKTOK: "TT caption",  # not connected
        }
        draft_ids = send_to_postiz(
            postiz=mock_postiz,
            captions=captions,
            media_url=None,
            scheduled_at=None,
        )
        assert len(draft_ids) == 1

    def test_passes_media_url_when_provided(self) -> None:
        from app.helpers.create_post_helpers import send_to_postiz

        mock_postiz = MagicMock()
        mock_postiz.list_integrations.return_value = [
            {"id": "int_ig", "platform": "instagram"},
        ]
        mock_postiz.create_draft_post.return_value = {"id": "draft_1"}

        captions = {Platform.INSTAGRAM: "IG caption"}
        send_to_postiz(
            postiz=mock_postiz,
            captions=captions,
            media_url="https://drive.google.com/file/d/abc/view",
            scheduled_at=None,
        )
        call_kwargs = mock_postiz.create_draft_post.call_args
        assert call_kwargs.kwargs.get("media_url") == "https://drive.google.com/file/d/abc/view"

    def test_passes_scheduled_at_when_provided(self) -> None:
        from app.helpers.create_post_helpers import send_to_postiz

        mock_postiz = MagicMock()
        mock_postiz.list_integrations.return_value = [
            {"id": "int_ig", "platform": "instagram"},
        ]
        mock_postiz.create_draft_post.return_value = {"id": "draft_1"}

        captions = {Platform.INSTAGRAM: "IG caption"}
        send_to_postiz(
            postiz=mock_postiz,
            captions=captions,
            media_url=None,
            scheduled_at="2026-03-01T10:00:00",
        )
        call_kwargs = mock_postiz.create_draft_post.call_args
        assert call_kwargs.kwargs.get("scheduled_at") == "2026-03-01T10:00:00"

    def test_returns_empty_when_no_integrations(self) -> None:
        from app.helpers.create_post_helpers import send_to_postiz

        mock_postiz = MagicMock()
        mock_postiz.list_integrations.return_value = []

        captions = {Platform.INSTAGRAM: "IG caption"}
        draft_ids = send_to_postiz(
            postiz=mock_postiz,
            captions=captions,
            media_url=None,
            scheduled_at=None,
        )
        assert draft_ids == []
