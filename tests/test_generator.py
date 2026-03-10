"""Tests for Claude CLI AI generator with mocked subprocess."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from content_engine.generator import BRAND_RULES, PLATFORM_INSTRUCTIONS, CaptionGenerator
from content_engine.models import ContentPillar, ContentRow, ContentStatus, Platform, Suggestion

SAMPLE_CLAUDE_OUTPUT = json.dumps(
    {
        "instagram": "Baby calf alert! Meet our newest resident at Gita Valley! "
        "This little one joined our herd of 85+ cows this morning. "
        "#farmlife #cowsanctuary #gitavalley #slaughterfree #babycalf",
        "facebook": "We have exciting news from the barn this morning! "
        "A beautiful baby calf was born at Gita Valley, joining our family of 85+ cows. "
        "Want to visit? gitavalley.org",
    }
)


@pytest.fixture
def generator(tmp_path):
    return CaptionGenerator(data_dir=tmp_path)


@pytest.fixture
def sample_row():
    return ContentRow(
        row_number=2,
        date=datetime(2026, 3, 1),
        content_pillar=ContentPillar.COW_LIFE,
        raw_text="Baby calf born this morning!",
        media_url="https://drive.google.com/file/d/abc123",
        platforms={Platform.INSTAGRAM: True, Platform.FACEBOOK: True, Platform.TIKTOK: False},
        status=ContentStatus.READY,
        captions={},
    )


class TestBrandRules:
    def test_brand_rules_contain_gita_valley(self) -> None:
        assert "Gita Valley" in BRAND_RULES

    def test_brand_rules_contain_slaughter_free(self) -> None:
        assert "Slaughter-Free" in BRAND_RULES

    def test_platform_instructions_all_platforms(self) -> None:
        for platform in Platform:
            assert platform in PLATFORM_INSTRUCTIONS


class TestBuildPrompt:
    def test_prompt_includes_brand_rules(self, generator, sample_row) -> None:
        platforms = [Platform.INSTAGRAM, Platform.FACEBOOK]
        prompt = generator._build_prompt(sample_row, platforms)

        assert "Gita Valley" in prompt
        assert sample_row.raw_text in prompt

    def test_prompt_includes_platform_instructions(self, generator, sample_row) -> None:
        platforms = [Platform.INSTAGRAM]
        prompt = generator._build_prompt(sample_row, platforms)

        assert "instagram" in prompt.lower()
        assert "hashtag" in prompt.lower()

    def test_prompt_includes_learning_context(self, generator, sample_row) -> None:
        generator.learning_context = {"top_performing_pillars": ["Cow Life"]}
        platforms = [Platform.INSTAGRAM]
        prompt = generator._build_prompt(sample_row, platforms)

        assert "Cow Life" in prompt

    def test_prompt_requests_json_output(self, generator, sample_row) -> None:
        platforms = [Platform.INSTAGRAM]
        prompt = generator._build_prompt(sample_row, platforms)

        assert "json" in prompt.lower()


class TestGenerateCaptions:
    @patch("content_engine.generator.subprocess.run")
    def test_returns_captions_for_requested_platforms(
        self, mock_run, generator, sample_row
    ) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=SAMPLE_CLAUDE_OUTPUT,
            stderr="",
        )

        captions = generator.generate_captions(sample_row)

        assert Platform.INSTAGRAM in captions
        assert Platform.FACEBOOK in captions
        assert Platform.TIKTOK not in captions
        assert "Gita Valley" in captions[Platform.INSTAGRAM]

    @patch("content_engine.generator.subprocess.run")
    def test_raises_on_cli_failure(self, mock_run, generator, sample_row) -> None:
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Not authenticated",
        )

        with pytest.raises(RuntimeError, match="Claude CLI"):
            generator.generate_captions(sample_row)

    @patch("content_engine.generator.subprocess.run")
    def test_handles_cli_timeout(self, mock_run, generator, sample_row) -> None:
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=120)

        with pytest.raises(RuntimeError, match="timed out"):
            generator.generate_captions(sample_row)


class TestInferPillar:
    @patch("content_engine.generator.subprocess.run")
    def test_returns_valid_pillar(self, mock_run, generator) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Cow Life",
            stderr="",
        )

        pillar = generator.infer_pillar("Our cows enjoying the morning sunshine")
        assert pillar == ContentPillar.COW_LIFE

    @patch("content_engine.generator.subprocess.run")
    def test_returns_community_for_event_text(self, mock_run, generator) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Community",
            stderr="",
        )

        pillar = generator.infer_pillar("Join us for the spring festival")
        assert pillar == ContentPillar.COMMUNITY


class TestGenerateSuggestions:
    @patch("content_engine.generator.subprocess.run")
    def test_returns_suggestions(self, mock_run, generator) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(
                [
                    {
                        "date": "2026-03-15",
                        "idea": "Spring planting photo series",
                        "pillar": "Farm Ops",
                        "rationale": "Spring content performs well",
                        "media": "Photos of seedlings",
                    }
                ]
            ),
            stderr="",
        )

        suggestions = generator.generate_suggestions(
            calendar_gaps=["2026-03-15", "2026-03-16"],
            pillar_balance={"Cow Life": 0.5, "Farm Ops": 0.1},
        )

        assert len(suggestions) == 1
        assert isinstance(suggestions[0], Suggestion)
        assert suggestions[0].suggested_pillar == ContentPillar.FARM_OPS


class TestLearningContext:
    def test_loads_empty_when_no_file(self, generator) -> None:
        assert generator.learning_context == {}

    def test_loads_from_file(self, tmp_path) -> None:
        ctx = {"top_performing_pillars": ["Cow Life"], "insights": ["cows do well"]}
        (tmp_path / "learning-context.json").write_text(json.dumps(ctx))

        gen = CaptionGenerator(data_dir=tmp_path)
        assert gen.learning_context["top_performing_pillars"] == ["Cow Life"]
