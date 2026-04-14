"""Tests for two-stage pipeline integration in CaptionGenerator."""

import json
from datetime import datetime
from unittest.mock import patch

import pytest

from content_engine.generator import CaptionGenerator
from content_engine.models import ContentRow, Platform


@pytest.fixture
def generator(tmp_path):
    (tmp_path / "voice-profile.json").write_text("{}")
    (tmp_path / "learned-rules.json").write_text('{"rules": []}')
    return CaptionGenerator(data_dir=tmp_path, db_path=str(tmp_path / "t.db"))


@pytest.fixture
def row():
    return ContentRow(
        row_number=1,
        date=datetime(2026, 3, 24),
        raw_text="Baby calf born this morning at the farm",
        content_pillar="Cow Life",
        platforms={Platform.INSTAGRAM: True, Platform.FACEBOOK: True},
        status="draft",
        captions={},
    )


class TestTwoStagePipeline:
    @patch("content_engine.two_stage_generator._call_claude")
    def test_generate_captions_two_stage(self, mock_claude, generator, row):
        """Full pipeline: narrative → adapt → slop gate."""
        mock_claude.side_effect = [
            # Stage 1: core narrative
            json.dumps(
                {
                    "core_message": "New calf born at dawn",
                    "key_details": ["healthy", "mother is Nandini"],
                    "emotional_hook": "new life",
                    "cta": "Visit this weekend",
                }
            ),
            # Stage 2: instagram adaptation
            "Meet our newest family member! Born at dawn.",
            # Stage 2: facebook adaptation
            "Exciting news from the farm! A new calf arrived.",
        ]

        captions = generator.generate_captions_two_stage(row)
        assert Platform.INSTAGRAM in captions
        assert Platform.FACEBOOK in captions
        assert mock_claude.call_count == 3

    @patch("content_engine.two_stage_generator._call_claude")
    def test_empty_platforms(self, mock_claude, generator):
        row = ContentRow(
            row_number=1,
            date=datetime(2026, 3, 24),
            raw_text="Test",
            content_pillar="Cow Life",
            platforms={},
            status="draft",
            captions={},
        )
        captions = generator.generate_captions_two_stage(row)
        assert captions == {}
        assert mock_claude.call_count == 0

    @patch("content_engine.two_stage_generator._call_claude")
    def test_slop_gate_triggers_on_two_stage(self, mock_claude, generator, row):
        """Slop gate should also run on two-stage output."""
        mock_claude.side_effect = [
            # Stage 1
            json.dumps(
                {
                    "core_message": "test",
                    "key_details": [],
                    "emotional_hook": "warm",
                    "cta": "visit",
                }
            ),
            # Stage 2: sloppy IG caption
            "Every life is a blessing in this tapestry of farm life",
            # Stage 2: clean FB caption
            "New calf born this morning!",
            # Slop gate retry for full output
            '{"instagram": "Our newest calf arrived at dawn."}',
        ]

        captions = generator.generate_captions_two_stage(row)
        # Should have at least the clean FB caption
        assert Platform.FACEBOOK in captions
