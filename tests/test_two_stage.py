"""Tests for two-stage generation pipeline (Stage 1: core narrative)."""

import json
from unittest.mock import patch

import pytest

from content_engine.two_stage_generator import (
    CoreNarrative,
    TwoStageGenerator,
)


@pytest.fixture
def generator(tmp_path):
    (tmp_path / "voice-profile.json").write_text("{}")
    (tmp_path / "learned-rules.json").write_text('{"rules": []}')
    return TwoStageGenerator(data_dir=tmp_path)


class TestCoreNarrative:
    def test_dataclass_fields(self):
        cn = CoreNarrative(
            core_message="Baby calf born today",
            key_details=["morning arrival", "healthy"],
            emotional_hook="new life on the farm",
            cta="Come visit us this weekend",
        )
        assert cn.core_message == "Baby calf born today"
        assert len(cn.key_details) == 2
        assert cn.emotional_hook == "new life on the farm"
        assert cn.cta == "Come visit us this weekend"


class TestGenerateCoreNarrative:
    @patch("content_engine.two_stage_generator._call_claude")
    def test_returns_core_narrative(self, mock_claude, generator):
        mock_claude.return_value = json.dumps(
            {
                "core_message": "A new calf joined our herd",
                "key_details": ["born at dawn", "mother is Nandini"],
                "emotional_hook": "new beginnings",
                "cta": "Visit the farm to meet the little one",
            }
        )

        result = generator.generate_core_narrative(
            raw_text="Baby calf born this morning",
            pillar="Cow Life",
        )
        assert isinstance(result, CoreNarrative)
        assert "calf" in result.core_message.lower()
        assert len(result.key_details) >= 1

    @patch("content_engine.two_stage_generator._call_claude")
    def test_handles_markdown_wrapped_json(self, mock_claude, generator):
        mock_claude.return_value = (
            '```json\n{"core_message": "test", "key_details": [], '
            '"emotional_hook": "warm", "cta": "visit"}\n```'
        )

        result = generator.generate_core_narrative(raw_text="Test", pillar="Cow Life")
        assert result.core_message == "test"

    @patch("content_engine.two_stage_generator._call_claude")
    def test_retries_on_parse_failure(self, mock_claude, generator):
        """On first parse failure, retries with simpler prompt."""
        mock_claude.side_effect = [
            "Not valid JSON at all",
            json.dumps(
                {
                    "core_message": "recovered",
                    "key_details": [],
                    "emotional_hook": "warm",
                    "cta": "visit",
                }
            ),
        ]

        result = generator.generate_core_narrative(raw_text="Test", pillar="Cow Life")
        assert result.core_message == "recovered"
        assert mock_claude.call_count == 2

    @patch("content_engine.two_stage_generator._call_claude")
    def test_raises_after_all_retries_fail(self, mock_claude, generator):
        mock_claude.return_value = "still not json"

        with pytest.raises(RuntimeError, match="parse"):
            generator.generate_core_narrative(raw_text="Test", pillar="Cow Life")

    @patch("content_engine.two_stage_generator._call_claude")
    def test_includes_knowledge_context(self, mock_claude, generator):
        mock_claude.return_value = json.dumps(
            {
                "core_message": "test",
                "key_details": [],
                "emotional_hook": "warm",
                "cta": "visit",
            }
        )

        generator.generate_core_narrative(
            raw_text="Test",
            pillar="Cow Life",
            knowledge_context="Farm has 80 cows",
        )
        prompt = mock_claude.call_args[0][0]
        assert "80 cows" in prompt
