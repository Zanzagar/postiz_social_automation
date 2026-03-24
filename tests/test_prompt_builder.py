"""Tests for XML prompt builder module."""

import pytest

from content_engine.prompt_builder import PromptBuilder


@pytest.fixture
def voice_profile():
    return {
        "sentence_style": "Short declarative sentences.",
        "emotional_register": "Warm and gentle.",
        "length_range": "30-80 words",
        "what_works": ["Cow portraits with names", "Ultra-short scenic captions"],
        "what_to_avoid": ["Link-only posts", "Long fundraising paragraphs"],
        "sample_hooks": ["Nandini is a cow who requires extra care."],
    }


@pytest.fixture
def learned_rules():
    return ["Never use the word 'nestled'", "Avoid starting with 'In the heart of'"]


@pytest.fixture
def builder(voice_profile, learned_rules):
    return PromptBuilder(voice_profile=voice_profile, learned_rules=learned_rules)


@pytest.fixture
def empty_builder():
    return PromptBuilder()


# --- XML helper tests ---


class TestXmlHelpers:
    def test_wrap_xml_basic(self, builder):
        result = builder._wrap_xml("system", "Hello world")
        assert result == "<system>\nHello world\n</system>"

    def test_wrap_xml_with_attrs(self, builder):
        result = builder._wrap_xml("platform", "Instagram rules", name="instagram")
        assert '<platform name="instagram">' in result
        assert "Instagram rules" in result
        assert "</platform>" in result

    def test_escape_xml_entities(self, builder):
        result = builder._escape("5 < 10 & 'quotes' are \"fine\"")
        assert "&lt;" in result
        assert "&amp;" in result
        assert "<" not in result.replace("&lt;", "")

    def test_escape_prevents_tag_injection(self, builder):
        malicious = '<script>alert("xss")</script>'
        result = builder._escape(malicious)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result


# --- Generation prompt tests ---


class TestBuildGenerationPrompt:
    def test_contains_system_section(self, builder):
        prompt = builder.build_generation_prompt(
            raw_text="Cows grazing at sunrise",
            pillar="Cow Life",
            platforms=["instagram", "facebook"],
        )
        assert "<system>" in prompt
        assert "</system>" in prompt
        assert "Gita Valley" in prompt

    def test_contains_voice_section(self, builder):
        prompt = builder.build_generation_prompt(
            raw_text="Cows grazing",
            pillar="Cow Life",
            platforms=["instagram"],
        )
        assert "<voice>" in prompt
        assert "</voice>" in prompt
        assert "Short declarative sentences" in prompt

    def test_contains_rules_section_when_rules_exist(self, builder):
        prompt = builder.build_generation_prompt(
            raw_text="Test", pillar="Cow Life", platforms=["instagram"]
        )
        assert "<rules>" in prompt
        assert "Never use the word 'nestled'" in prompt

    def test_no_rules_section_when_empty(self, empty_builder):
        prompt = empty_builder.build_generation_prompt(
            raw_text="Test", pillar="Cow Life", platforms=["instagram"]
        )
        assert "<rules>" not in prompt

    def test_contains_content_section(self, builder):
        prompt = builder.build_generation_prompt(
            raw_text="Baby calf born today!",
            pillar="Cow Life",
            platforms=["instagram"],
        )
        assert "<content>" in prompt
        assert "Baby calf born today!" in prompt
        assert "Cow Life" in prompt

    def test_contains_constraints_per_platform(self, builder):
        prompt = builder.build_generation_prompt(
            raw_text="Test",
            pillar="Farm Ops",
            platforms=["instagram", "facebook"],
        )
        assert "<constraints>" in prompt
        assert "instagram" in prompt.lower()
        assert "facebook" in prompt.lower()

    def test_contains_output_format(self, builder):
        prompt = builder.build_generation_prompt(
            raw_text="Test",
            pillar="Cow Life",
            platforms=["instagram"],
        )
        assert "<output_format>" in prompt
        assert "JSON" in prompt

    def test_knowledge_context_injected(self, builder):
        prompt = builder.build_generation_prompt(
            raw_text="Test",
            pillar="Cow Life",
            platforms=["instagram"],
            knowledge_context="Gita Valley has 80 cows on 430 acres.",
        )
        assert "<knowledge>" in prompt
        assert "80 cows" in prompt

    def test_no_knowledge_section_when_empty(self, builder):
        prompt = builder.build_generation_prompt(
            raw_text="Test",
            pillar="Cow Life",
            platforms=["instagram"],
        )
        assert "<knowledge>" not in prompt

    def test_media_flag_included(self, builder):
        prompt = builder.build_generation_prompt(
            raw_text="Test",
            pillar="Cow Life",
            platforms=["instagram"],
            has_media=True,
        )
        assert "media" in prompt.lower()

    def test_user_content_is_escaped(self, builder):
        prompt = builder.build_generation_prompt(
            raw_text='Use <b>bold</b> & "quotes"',
            pillar="Cow Life",
            platforms=["instagram"],
        )
        assert "<b>" not in prompt
        assert "&lt;b&gt;" in prompt

    def test_prompt_size_reasonable(self, builder):
        prompt = builder.build_generation_prompt(
            raw_text="Cows grazing at sunrise",
            pillar="Cow Life",
            platforms=["instagram", "facebook", "tiktok"],
            knowledge_context="Some facts about the farm." * 10,
        )
        # Rough token estimate: ~4 chars per token, should be under 4000 tokens
        assert len(prompt) < 16000


# --- Iteration prompt tests ---


class TestBuildIterationPrompt:
    def test_contains_original_caption(self, builder):
        prompt = builder.build_iteration_prompt(
            original_caption="Check out our cows!",
            platform="instagram",
            instruction="Make it shorter",
            raw_text="Cow update",
            pillar="Cow Life",
        )
        assert "<content>" in prompt
        assert "Check out our cows!" in prompt

    def test_contains_instruction(self, builder):
        prompt = builder.build_iteration_prompt(
            original_caption="Test caption",
            platform="facebook",
            instruction="Add a question at the end",
            raw_text="Test",
            pillar="Cow Life",
        )
        assert "<instruction>" in prompt
        assert "Add a question at the end" in prompt

    def test_no_knowledge_in_iteration(self, builder):
        """Iterations should NOT include knowledge context (causes shoehorning)."""
        prompt = builder.build_iteration_prompt(
            original_caption="Test",
            platform="instagram",
            instruction="Improve",
            raw_text="Test",
            pillar="Cow Life",
        )
        assert "<knowledge>" not in prompt

    def test_platform_constraints_present(self, builder):
        prompt = builder.build_iteration_prompt(
            original_caption="Test",
            platform="tiktok",
            instruction="Improve",
            raw_text="Test",
            pillar="Cow Life",
        )
        assert "<constraints>" in prompt
        assert "tiktok" in prompt.lower()

    def test_output_is_plain_text_not_json(self, builder):
        prompt = builder.build_iteration_prompt(
            original_caption="Test",
            platform="instagram",
            instruction="Improve",
            raw_text="Test",
            pillar="Cow Life",
        )
        assert "<output_format>" in prompt
        # Should request plain caption text, not JSON
        assert "ONLY the caption" in prompt or "caption text" in prompt.lower()


# --- Suggestion prompt tests ---


class TestBuildSuggestionPrompt:
    def test_contains_calendar_gaps(self, builder):
        prompt = builder.build_suggestion_prompt(
            calendar_gaps=["2026-04-01", "2026-04-03"],
            pillar_balance={"Cow Life": 0.4, "Farm Ops": 0.2},
        )
        assert "<content>" in prompt
        assert "2026-04-01" in prompt
        assert "2026-04-03" in prompt

    def test_contains_pillar_balance(self, builder):
        prompt = builder.build_suggestion_prompt(
            calendar_gaps=["2026-04-01"],
            pillar_balance={"Cow Life": 0.4},
        )
        assert "Cow Life" in prompt

    def test_knowledge_included_for_suggestions(self, builder):
        prompt = builder.build_suggestion_prompt(
            calendar_gaps=["2026-04-01"],
            pillar_balance={},
            knowledge_context="Farm has 430 acres.",
        )
        assert "<knowledge>" in prompt
        assert "430 acres" in prompt

    def test_output_format_is_json_array(self, builder):
        prompt = builder.build_suggestion_prompt(
            calendar_gaps=["2026-04-01"],
            pillar_balance={},
        )
        assert "<output_format>" in prompt
        assert "JSON" in prompt


# --- Calendar prompt tests ---


class TestBuildCalendarPrompt:
    def test_contains_date_range(self, builder):
        prompt = builder.build_calendar_prompt(
            start_date="2026-04-01",
            end_date="2026-04-30",
            platforms=["instagram", "facebook"],
            pillar_weights={"Cow Life": 0.4, "Farm Ops": 0.25},
        )
        assert "2026-04-01" in prompt
        assert "2026-04-30" in prompt

    def test_contains_festivals(self, builder):
        festivals = [{"name": "Rama Navami", "date": "2026-04-05"}]
        prompt = builder.build_calendar_prompt(
            start_date="2026-04-01",
            end_date="2026-04-30",
            platforms=["instagram"],
            pillar_weights={},
            festivals=festivals,
        )
        assert "Rama Navami" in prompt

    def test_contains_pillar_weights(self, builder):
        prompt = builder.build_calendar_prompt(
            start_date="2026-04-01",
            end_date="2026-04-30",
            platforms=["instagram"],
            pillar_weights={"Cow Life": 0.4, "Farm Ops": 0.25},
        )
        assert "Cow Life" in prompt
        assert "0.4" in prompt

    def test_output_format_is_json(self, builder):
        prompt = builder.build_calendar_prompt(
            start_date="2026-04-01",
            end_date="2026-04-30",
            platforms=["instagram"],
            pillar_weights={},
        )
        assert "<output_format>" in prompt
        assert "JSON" in prompt


# --- Few-shot examples tests ---


class TestFewShotExamples:
    def test_examples_section_when_provided(self, builder):
        examples = [
            {"input": "Cow update", "output": "Meet Nandini! She loves morning walks."},
        ]
        prompt = builder.build_generation_prompt(
            raw_text="Test",
            pillar="Cow Life",
            platforms=["instagram"],
            few_shot_examples=examples,
        )
        assert "<examples>" in prompt
        assert "Nandini" in prompt

    def test_no_examples_section_when_empty(self, builder):
        prompt = builder.build_generation_prompt(
            raw_text="Test",
            pillar="Cow Life",
            platforms=["instagram"],
        )
        assert "<examples>" not in prompt
