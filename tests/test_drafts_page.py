"""Tests for the Drafts Review page (Task 13).

Tests verify:
- Page file exists
- Enabled platform extraction from ContentRow
- Caption retrieval per platform
- Postiz link construction
- Batch approval data preparation
- Caption edit application
"""

from datetime import datetime
from pathlib import Path

from content_engine.models import ContentRow, ContentStatus, Platform


def _make_draft(**overrides) -> ContentRow:
    """Factory for test drafts."""
    defaults = {
        "row_number": 2,
        "date": datetime(2026, 3, 1),
        "content_pillar": "Cow Life",
        "raw_text": "Lakshmi enjoying the morning sun",
        "media_url": None,
        "platforms": {
            Platform.INSTAGRAM: True,
            Platform.FACEBOOK: True,
            Platform.TIKTOK: False,
            Platform.THREADS: False,
            Platform.LINKEDIN: False,
        },
        "status": ContentStatus.PENDING_APPROVAL,
        "captions": {
            Platform.INSTAGRAM: "IG caption here",
            Platform.FACEBOOK: "FB caption here",
            Platform.TIKTOK: None,
            Platform.THREADS: None,
            Platform.LINKEDIN: None,
        },
        "postiz_ids": "abc123,def456",
    }
    defaults.update(overrides)
    return ContentRow(**defaults)


class TestDraftsPageExists:
    def test_page_file_exists(self) -> None:
        page = Path("app/pages/6_Drafts.py")
        assert page.exists(), f"Drafts page not found at {page}"


class TestGetEnabledPlatforms:
    """Test extraction of enabled platforms from a ContentRow."""

    def test_returns_only_true_platforms(self) -> None:
        from app.helpers.drafts_helpers import get_enabled_platforms

        draft = _make_draft()
        result = get_enabled_platforms(draft)
        assert result == [Platform.INSTAGRAM, Platform.FACEBOOK]

    def test_returns_empty_when_none_enabled(self) -> None:
        from app.helpers.drafts_helpers import get_enabled_platforms

        draft = _make_draft(
            platforms={p: False for p in Platform},
        )
        result = get_enabled_platforms(draft)
        assert result == []

    def test_returns_all_when_all_enabled(self) -> None:
        from app.helpers.drafts_helpers import get_enabled_platforms

        draft = _make_draft(
            platforms={p: True for p in Platform},
        )
        result = get_enabled_platforms(draft)
        assert len(result) == 5


class TestGetCaptionForPlatform:
    """Test caption retrieval for a specific platform."""

    def test_returns_caption_text(self) -> None:
        from app.helpers.drafts_helpers import get_caption_for_platform

        draft = _make_draft()
        assert get_caption_for_platform(draft, Platform.INSTAGRAM) == "IG caption here"

    def test_returns_empty_string_for_none_caption(self) -> None:
        from app.helpers.drafts_helpers import get_caption_for_platform

        draft = _make_draft()
        assert get_caption_for_platform(draft, Platform.TIKTOK) == ""

    def test_returns_empty_string_for_missing_platform(self) -> None:
        from app.helpers.drafts_helpers import get_caption_for_platform

        draft = _make_draft(captions={})
        assert get_caption_for_platform(draft, Platform.INSTAGRAM) == ""


class TestBuildPostizLink:
    """Test Postiz URL construction."""

    def test_returns_link_when_ids_present(self) -> None:
        from app.helpers.drafts_helpers import build_postiz_link

        link = build_postiz_link("abc123", base_url="https://postiz.sethpc.xyz")
        assert link == "https://postiz.sethpc.xyz/posts/abc123"

    def test_returns_none_when_ids_none(self) -> None:
        from app.helpers.drafts_helpers import build_postiz_link

        assert build_postiz_link(None) is None

    def test_returns_none_when_ids_empty(self) -> None:
        from app.helpers.drafts_helpers import build_postiz_link

        assert build_postiz_link("") is None


class TestPrepareBatchApprove:
    """Test batch approval data preparation."""

    def test_returns_list_of_dicts_with_row_data(self) -> None:
        from app.helpers.drafts_helpers import prepare_batch_approve

        drafts = [
            _make_draft(row_number=2),
            _make_draft(row_number=5, raw_text="Farm tour video"),
        ]
        result = prepare_batch_approve(drafts)
        assert len(result) == 2
        assert result[0]["row_number"] == 2
        assert result[1]["row_number"] == 5

    def test_includes_enabled_platforms(self) -> None:
        from app.helpers.drafts_helpers import prepare_batch_approve

        drafts = [_make_draft()]
        result = prepare_batch_approve(drafts)
        assert Platform.INSTAGRAM in result[0]["enabled_platforms"]
        assert Platform.FACEBOOK in result[0]["enabled_platforms"]
        assert Platform.TIKTOK not in result[0]["enabled_platforms"]

    def test_empty_list_returns_empty(self) -> None:
        from app.helpers.drafts_helpers import prepare_batch_approve

        assert prepare_batch_approve([]) == []


class TestApplyCaptionEdits:
    """Test applying inline caption edits to a draft."""

    def test_applies_edits_to_matching_platforms(self) -> None:
        from app.helpers.drafts_helpers import apply_caption_edits

        draft = _make_draft()
        edits = {Platform.INSTAGRAM: "Edited IG caption"}
        result = apply_caption_edits(draft, edits)
        assert result.captions[Platform.INSTAGRAM] == "Edited IG caption"
        assert result.captions[Platform.FACEBOOK] == "FB caption here"  # unchanged

    def test_preserves_original_when_no_edits(self) -> None:
        from app.helpers.drafts_helpers import apply_caption_edits

        draft = _make_draft()
        result = apply_caption_edits(draft, {})
        assert result.captions == draft.captions

    def test_returns_new_instance(self) -> None:
        from app.helpers.drafts_helpers import apply_caption_edits

        draft = _make_draft()
        result = apply_caption_edits(draft, {Platform.INSTAGRAM: "New"})
        assert result is not draft
