"""Tests for content validation module."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from content_engine.models import ContentRow, ContentStatus, Platform
from content_engine.validator import ContentValidator


def _make_row(**overrides) -> ContentRow:
    """Helper to create a ContentRow with sensible defaults."""
    defaults = {
        "row_number": 1,
        "date": datetime(2026, 3, 1),
        "content_pillar": "Cow Life",
        "raw_text": "Baby calf born this morning!",
        "platforms": {Platform.INSTAGRAM: True},
        "status": ContentStatus.READY,
        "captions": {},
    }
    defaults.update(overrides)
    return ContentRow(**defaults)


class TestValidateRow:
    def test_valid_row_passes(self) -> None:
        validator = ContentValidator()
        is_valid, error = validator.validate_row(_make_row())
        assert is_valid is True
        assert error is None

    def test_missing_raw_text_fails(self) -> None:
        validator = ContentValidator()
        is_valid, error = validator.validate_row(_make_row(raw_text=""))
        assert is_valid is False
        assert "raw_text" in error.lower()

    def test_whitespace_only_raw_text_fails(self) -> None:
        validator = ContentValidator()
        is_valid, error = validator.validate_row(_make_row(raw_text="   "))
        assert is_valid is False

    def test_no_platforms_selected_fails(self) -> None:
        validator = ContentValidator()
        row = _make_row(platforms={Platform.INSTAGRAM: False, Platform.FACEBOOK: False})
        is_valid, error = validator.validate_row(row)
        assert is_valid is False
        assert "platform" in error.lower()

    def test_empty_platforms_dict_fails(self) -> None:
        validator = ContentValidator()
        is_valid, error = validator.validate_row(_make_row(platforms={}))
        assert is_valid is False

    @patch("content_engine.validator.requests.head")
    def test_accessible_media_url_passes(self, mock_head) -> None:
        mock_head.return_value = MagicMock(status_code=200)
        validator = ContentValidator()
        row = _make_row(media_url="https://drive.google.com/file/d/abc123")
        is_valid, error = validator.validate_row(row)
        assert is_valid is True

    @patch("content_engine.validator.requests.head")
    def test_inaccessible_media_url_fails(self, mock_head) -> None:
        mock_head.return_value = MagicMock(status_code=404)
        validator = ContentValidator()
        row = _make_row(media_url="https://drive.google.com/file/d/bad")
        is_valid, error = validator.validate_row(row)
        assert is_valid is False
        assert "media" in error.lower()

    @patch("content_engine.validator.requests.head")
    def test_media_url_timeout_fails(self, mock_head) -> None:
        import requests

        mock_head.side_effect = requests.Timeout
        validator = ContentValidator()
        row = _make_row(media_url="https://drive.google.com/file/d/slow")
        is_valid, error = validator.validate_row(row)
        assert is_valid is False

    def test_no_media_url_is_valid(self) -> None:
        validator = ContentValidator()
        row = _make_row(media_url=None)
        is_valid, error = validator.validate_row(row)
        assert is_valid is True


class TestValidateMediaFormat:
    @patch("content_engine.validator.requests.head")
    def test_jpeg_is_supported(self, mock_head) -> None:
        mock_head.return_value = MagicMock(status_code=200, headers={"Content-Type": "image/jpeg"})
        validator = ContentValidator()
        is_valid, error = validator.validate_media_format("https://example.com/photo.jpg")
        assert is_valid is True

    @patch("content_engine.validator.requests.head")
    def test_unsupported_format_fails(self, mock_head) -> None:
        mock_head.return_value = MagicMock(
            status_code=200, headers={"Content-Type": "application/pdf"}
        )
        validator = ContentValidator()
        is_valid, error = validator.validate_media_format("https://example.com/doc.pdf")
        assert is_valid is False
        assert "format" in error.lower()
