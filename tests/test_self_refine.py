"""Tests for self-refine scoring loop."""

import json
from unittest.mock import patch

from content_engine.self_refine import QualityScore, score_caption


class TestQualityScore:
    def test_overall_is_average(self):
        qs = QualityScore(
            voice_match=8, platform_fit=6, specificity=10, slop_free=8, feedback="good"
        )
        assert qs.overall == 8.0

    def test_needs_refinement_below_threshold(self):
        qs = QualityScore(
            voice_match=5, platform_fit=5, specificity=5, slop_free=5, feedback="generic"
        )
        assert qs.overall < 7
        assert qs.needs_refinement()

    def test_no_refinement_above_threshold(self):
        qs = QualityScore(
            voice_match=8, platform_fit=8, specificity=8, slop_free=8, feedback="great"
        )
        assert not qs.needs_refinement()


class TestScoreCaption:
    @patch("content_engine.self_refine._call_claude")
    def test_returns_quality_score(self, mock_claude):
        mock_claude.return_value = json.dumps(
            {
                "voice_match": 8,
                "platform_fit": 7,
                "specificity": 9,
                "slop_free": 8,
                "feedback": "Good use of cow name",
            }
        )

        score = score_caption(
            "Meet Nandini! She loves morning walks.",
            "instagram",
        )
        assert isinstance(score, QualityScore)
        assert score.voice_match == 8
        assert score.overall == 8.0

    @patch("content_engine.self_refine._call_claude")
    def test_handles_parse_failure(self, mock_claude):
        mock_claude.return_value = "not json"

        score = score_caption("test caption", "instagram")
        # Should return a default low score
        assert score.overall <= 5

    @patch("content_engine.self_refine._call_claude")
    def test_uses_haiku_model(self, mock_claude):
        mock_claude.return_value = json.dumps(
            {
                "voice_match": 7,
                "platform_fit": 7,
                "specificity": 7,
                "slop_free": 7,
                "feedback": "ok",
            }
        )

        score_caption("test", "instagram")
        # Check that model="haiku" was passed
        call_kwargs = mock_claude.call_args
        assert call_kwargs[1].get("model") == "haiku" or "haiku" in str(call_kwargs)
