"""Tests for two-stage generation pipeline (Stage 2: platform adaptation)."""

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


@pytest.fixture
def narrative():
    return CoreNarrative(
        core_message="A new calf was born this morning at Gita Valley",
        key_details=["born at dawn", "mother is Nandini", "healthy"],
        emotional_hook="new beginnings on the farm",
        cta="Visit us this weekend to meet the little one",
    )


class TestAdaptToPlatform:
    @patch("content_engine.two_stage_generator._call_claude")
    def test_returns_caption_string(self, mock_claude, generator, narrative):
        mock_claude.return_value = "Meet our newest resident! Born at dawn."
        result = generator.adapt_to_platform(narrative, "instagram")
        assert isinstance(result, str)
        assert len(result) > 0

    @patch("content_engine.two_stage_generator._call_claude")
    def test_includes_platform_in_prompt(self, mock_claude, generator, narrative):
        mock_claude.return_value = "test caption"
        generator.adapt_to_platform(narrative, "facebook")
        prompt = mock_claude.call_args[0][0]
        assert "facebook" in prompt.lower()

    @patch("content_engine.two_stage_generator._call_claude")
    def test_includes_core_message(self, mock_claude, generator, narrative):
        mock_claude.return_value = "test"
        generator.adapt_to_platform(narrative, "instagram")
        prompt = mock_claude.call_args[0][0]
        assert "new calf" in prompt.lower()


class TestAdaptToAllPlatforms:
    @patch("content_engine.two_stage_generator._call_claude")
    def test_returns_dict_of_captions(self, mock_claude, generator, narrative):
        mock_claude.side_effect = [
            "IG caption here",
            "FB caption here",
        ]
        result = generator.adapt_to_all_platforms(narrative, ["instagram", "facebook"])
        assert "instagram" in result
        assert "facebook" in result
        assert result["instagram"] == "IG caption here"

    @patch("content_engine.two_stage_generator._call_claude")
    def test_handles_single_platform(self, mock_claude, generator, narrative):
        mock_claude.return_value = "TikTok caption"
        result = generator.adapt_to_all_platforms(narrative, ["tiktok"])
        assert len(result) == 1
        assert result["tiktok"] == "TikTok caption"

    @patch("content_engine.two_stage_generator._call_claude")
    def test_handles_failure_gracefully(self, mock_claude, generator, narrative):
        """If one platform fails, others should still succeed."""
        mock_claude.side_effect = [
            RuntimeError("Claude failed"),
            "FB caption works",
        ]
        result = generator.adapt_to_all_platforms(narrative, ["instagram", "facebook"])
        assert "facebook" in result
        assert "instagram" not in result  # Failed platform excluded
