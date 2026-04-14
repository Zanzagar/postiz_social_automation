"""Tests for slop gate integration in caption generation."""

from unittest.mock import patch

import pytest

from content_engine.generator import CaptionGenerator
from content_engine.models import ContentRow, Platform


@pytest.fixture
def generator(tmp_path):
    # Create minimal data dir with empty voice profile
    (tmp_path / "voice-profile.json").write_text("{}")
    (tmp_path / "learned-rules.json").write_text('{"rules": []}')
    return CaptionGenerator(data_dir=tmp_path, db_path=str(tmp_path / "test.db"))


@pytest.fixture
def row():
    from datetime import datetime

    return ContentRow(
        row_number=1,
        date=datetime(2026, 3, 24),
        raw_text="Baby calf born this morning",
        content_pillar="Cow Life",
        platforms={Platform.INSTAGRAM: True},
        status="draft",
        captions={},
    )


class TestSlopGate:
    @patch("content_engine.generator._call_claude")
    def test_clean_caption_passes_through(self, mock_claude, generator, row):
        """Captions below threshold are returned directly."""
        mock_claude.return_value = '{"instagram": "Meet our newest calf!"}'

        result = generator.generate_captions(row)
        assert result[Platform.INSTAGRAM] == "Meet our newest calf!"
        assert mock_claude.call_count == 1  # No regeneration

    @patch("content_engine.generator._call_claude")
    def test_sloppy_caption_triggers_retry(self, mock_claude, generator, row):
        """Captions above threshold trigger one regeneration attempt."""
        # First call returns sloppy text, second returns clean
        mock_claude.side_effect = [
            '{"instagram": "Every life is a blessing in this tapestry of farm life"}',
            '{"instagram": "Our newest calf arrived at dawn."}',
        ]

        result = generator.generate_captions(row)
        assert mock_claude.call_count == 2
        # Should return the cleaner version
        assert "tapestry" not in result[Platform.INSTAGRAM]

    @patch("content_engine.generator._call_claude")
    def test_max_one_retry(self, mock_claude, generator, row):
        """Slop gate only retries once, even if second attempt is sloppy."""
        mock_claude.side_effect = [
            '{"instagram": "Every life is a blessing in this tapestry of love"}',
            '{"instagram": "Hearts overflowing on this incredible journey"}',
        ]

        generator.generate_captions(row)
        # Should only call twice (original + 1 retry)
        assert mock_claude.call_count == 2
        # Returns best of two attempts

    @patch("content_engine.generator._call_claude")
    def test_returns_best_of_two(self, mock_claude, generator, row):
        """When both attempts are sloppy, returns the one with lower score."""
        mock_claude.side_effect = [
            '{"instagram": "Every life is a blessing in this '
            'tapestry of love and the hearts overflowing"}',
            '{"instagram": "A gentle moment on this incredible journey"}',
        ]

        result = generator.generate_captions(row)
        # Second is less sloppy, should be returned
        assert "incredible journey" in result[Platform.INSTAGRAM]

    @patch("content_engine.generator._call_claude")
    def test_slop_warning_flag(self, mock_claude, generator, row):
        """Generator should have slop_warning attribute after sloppy result."""
        mock_claude.side_effect = [
            '{"instagram": "Every life is a blessing in this tapestry"}',
            '{"instagram": "A gentle moment on this incredible journey"}',
        ]

        generator.generate_captions(row)
        # After generation, last_slop_result should exist
        assert hasattr(generator, "last_slop_result")
