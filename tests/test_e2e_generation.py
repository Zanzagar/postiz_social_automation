"""End-to-end integration test for the content generation pipeline.

Tests the full flow: prompt building → Claude CLI → JSON parsing →
slop detection → two-stage generation → self-refine scoring.
All Claude calls are mocked.
"""

import json
from datetime import datetime
from unittest.mock import patch

import pytest

from content_engine.generator import CaptionGenerator
from content_engine.models import ContentRow, Platform
from content_engine.prompt_builder import PromptBuilder
from content_engine.self_refine import score_caption
from content_engine.slop_detector import SlopDetector


@pytest.fixture
def generator(tmp_path):
    (tmp_path / "voice-profile.json").write_text(
        json.dumps(
            {
                "sentence_style": "Short, simple sentences.",
                "emotional_register": "Warm and gentle.",
                "what_works": ["Cow portraits with names"],
                "what_to_avoid": ["Link-only posts"],
            }
        )
    )
    (tmp_path / "learned-rules.json").write_text(json.dumps({"rules": ["Never use 'nestled'"]}))
    return CaptionGenerator(data_dir=tmp_path, db_path=str(tmp_path / "test.db"))


@pytest.fixture
def row():
    return ContentRow(
        row_number=1,
        date=datetime(2026, 3, 24),
        raw_text="Nandini the cow had a beautiful morning walk today",
        content_pillar="Cow Life",
        platforms={
            Platform.INSTAGRAM: True,
            Platform.FACEBOOK: True,
        },
        status="draft",
        captions={},
    )


class TestE2EPromptBuilder:
    """Verify prompt builder produces valid XML structure."""

    def test_generation_prompt_has_all_sections(self):
        pb = PromptBuilder(
            voice_profile={"sentence_style": "Short"},
            learned_rules=["No AI cliches"],
        )
        prompt = pb.build_generation_prompt(
            raw_text="Cows in the field",
            pillar="Cow Life",
            platforms=["instagram", "facebook"],
            knowledge_context="Farm has 80 cows.",
            few_shot_examples=[{"input": "cow", "output": "Meet Nandini!"}],
        )
        for tag in [
            "<system>",
            "<voice>",
            "<rules>",
            "<knowledge>",
            "<examples>",
            "<content>",
            "<constraints>",
            "<output_format>",
        ]:
            assert tag in prompt, f"Missing {tag}"


class TestE2ESlopDetection:
    """Verify slop detection works on real-ish text."""

    def test_clean_gita_valley_post(self):
        detector = SlopDetector()
        result = detector.detect(
            "Nandini had her morning walk today. She stopped to sniff the wildflowers by the creek."
        )
        assert result.score == 0.0

    def test_sloppy_ai_post(self):
        detector = SlopDetector()
        result = detector.detect(
            "Nestled in the rolling hills, our hearts overflowing "
            "with every life being a blessing. This incredible journey "
            "through the tapestry of farm life is truly remarkable."
        )
        assert result.is_slop()
        assert len(result.matches) >= 3


class TestE2EOneShot:
    """Full single-shot generation with mocked Claude."""

    @patch("content_engine.generator._call_claude")
    def test_generates_clean_captions(self, mock_claude, generator, row):
        mock_claude.return_value = json.dumps(
            {
                "instagram": "Nandini took her morning stroll by the creek today.",
                "facebook": "Morning walks with Nandini — she always stops "
                "for wildflowers. Have you visited the farm lately?",
            }
        )

        captions = generator.generate_captions(row)
        assert Platform.INSTAGRAM in captions
        assert Platform.FACEBOOK in captions
        assert "Nandini" in captions[Platform.INSTAGRAM]

    @patch("content_engine.generator._call_claude")
    def test_slop_gate_activates(self, mock_claude, generator, row):
        mock_claude.side_effect = [
            json.dumps(
                {
                    "instagram": "Every life is a blessing at the farm",
                    "facebook": "Hearts overflowing with tapestry of love",
                }
            ),
            json.dumps(
                {
                    "instagram": "Nandini strolled through the meadow.",
                    "facebook": "Morning walk with our oldest cow.",
                }
            ),
        ]

        generator.generate_captions(row)
        # Slop gate should have retried
        assert mock_claude.call_count == 2


class TestE2ETwoStage:
    """Full two-stage pipeline with mocked Claude."""

    @patch("content_engine.two_stage_generator._call_claude")
    def test_narrative_to_captions(self, mock_claude, generator, row):
        mock_claude.side_effect = [
            json.dumps(
                {
                    "core_message": "Nandini enjoyed her morning walk",
                    "key_details": ["creek", "wildflowers"],
                    "emotional_hook": "peaceful farm morning",
                    "cta": "Visit us this spring",
                }
            ),
            "Nandini at the creek this morning.",
            "Our oldest cow loves her morning routine. Visit us!",
        ]

        captions = generator.generate_captions_two_stage(row)
        assert Platform.INSTAGRAM in captions
        assert Platform.FACEBOOK in captions


class TestE2ESelfRefine:
    """Self-refine scoring on generated captions."""

    @patch("content_engine.self_refine._call_claude")
    def test_scores_clean_caption_high(self, mock_claude):
        mock_claude.return_value = json.dumps(
            {
                "voice_match": 9,
                "platform_fit": 8,
                "specificity": 9,
                "slop_free": 10,
                "feedback": "Excellent use of cow name and specific detail",
            }
        )

        score = score_caption(
            "Nandini stopped to sniff wildflowers this morning.",
            "instagram",
        )
        assert score.overall >= 8
        assert not score.needs_refinement()

    @patch("content_engine.self_refine._call_claude")
    def test_scores_sloppy_caption_low(self, mock_claude):
        mock_claude.return_value = json.dumps(
            {
                "voice_match": 3,
                "platform_fit": 5,
                "specificity": 2,
                "slop_free": 2,
                "feedback": "Generic AI language, no specifics",
            }
        )

        score = score_caption(
            "Every life is a blessing in this tapestry",
            "instagram",
        )
        assert score.overall < 7
        assert score.needs_refinement()
