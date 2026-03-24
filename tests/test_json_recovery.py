"""Tests for JSON recovery in _parse_response() — Task 18.

Covers recovery paths when Claude returns malformed or wrapped JSON:
- Valid JSON passes through unchanged
- JSON inside markdown fences is extracted
- JSON embedded in surrounding text is extracted
- Completely invalid text raises RuntimeError
"""

import json

import pytest

from content_engine.generator import CaptionGenerator
from content_engine.models import Platform


@pytest.fixture
def generator(tmp_path):
    return CaptionGenerator(data_dir=tmp_path)


PLATFORMS = [Platform.INSTAGRAM, Platform.FACEBOOK]


class TestJsonRecoveryValidJson:
    """Valid JSON should pass through without any recovery."""

    def test_clean_json_parsed(self, generator) -> None:
        raw = json.dumps({"instagram": "Hello world", "facebook": "Hi there"})
        result = generator._parse_response(raw, PLATFORMS)
        assert result[Platform.INSTAGRAM] == "Hello world"
        assert result[Platform.FACEBOOK] == "Hi there"


class TestJsonRecoveryMarkdownFence:
    """JSON wrapped in markdown code fences should be extracted."""

    def test_json_in_backtick_fence(self, generator) -> None:
        raw = '```json\n{"instagram": "cow pic", "facebook": "moo"}\n```'
        result = generator._parse_response(raw, PLATFORMS)
        assert result[Platform.INSTAGRAM] == "cow pic"

    def test_json_in_fence_without_language(self, generator) -> None:
        raw = '```\n{"instagram": "no lang", "facebook": "test"}\n```'
        result = generator._parse_response(raw, PLATFORMS)
        assert result[Platform.INSTAGRAM] == "no lang"


class TestJsonRecoveryEmbeddedText:
    """JSON embedded in surrounding prose should be extracted."""

    def test_json_after_preamble(self, generator) -> None:
        raw = (
            "Here are the captions I generated:\n\n"
            '{"instagram": "farm life", "facebook": "visit us"}'
        )
        result = generator._parse_response(raw, PLATFORMS)
        assert result[Platform.INSTAGRAM] == "farm life"
        assert result[Platform.FACEBOOK] == "visit us"

    def test_json_with_trailing_text(self, generator) -> None:
        raw = (
            '{"instagram": "sunrise at Gita Valley", "facebook": "good morning"}\n\n'
            "Let me know if you want changes!"
        )
        result = generator._parse_response(raw, PLATFORMS)
        assert result[Platform.INSTAGRAM] == "sunrise at Gita Valley"

    def test_json_surrounded_by_text(self, generator) -> None:
        raw = (
            "Sure, here you go:\n"
            '{"instagram": "calf born today", "facebook": "new baby"}\n'
            "Hope that helps!"
        )
        result = generator._parse_response(raw, PLATFORMS)
        assert result[Platform.INSTAGRAM] == "calf born today"


class TestJsonRecoveryInvalidText:
    """Completely invalid text should raise RuntimeError."""

    def test_no_json_at_all_raises(self, generator) -> None:
        raw = "I cannot generate captions for this content."
        with pytest.raises(RuntimeError, match="Could not parse"):
            generator._parse_response(raw, PLATFORMS)

    def test_partial_json_raises(self, generator) -> None:
        raw = '{"instagram": "incomplete'
        with pytest.raises(RuntimeError, match="Could not parse"):
            generator._parse_response(raw, PLATFORMS)

    def test_empty_string_raises(self, generator) -> None:
        with pytest.raises(RuntimeError, match="Could not parse"):
            generator._parse_response("", PLATFORMS)
