"""Tests for model configuration per task type (Task #14).

Tests cover:
- Default model mappings for each task type
- Environment variable overrides per task type
- Unknown task types fall back to sonnet
"""

from content_engine.model_config import DEFAULT_MODELS, get_model


class TestDefaultModels:
    def test_generate_defaults_to_sonnet(self):
        assert get_model("generate") == "sonnet"

    def test_iterate_defaults_to_sonnet(self):
        assert get_model("iterate") == "sonnet"

    def test_suggest_defaults_to_sonnet(self):
        assert get_model("suggest") == "sonnet"

    def test_calendar_defaults_to_sonnet(self):
        assert get_model("calendar") == "sonnet"

    def test_classify_defaults_to_haiku(self):
        assert get_model("classify") == "haiku"

    def test_all_expected_task_types_present(self):
        expected = {"generate", "iterate", "suggest", "calendar", "classify"}
        assert set(DEFAULT_MODELS.keys()) == expected


class TestEnvVarOverrides:
    def test_override_generate_model(self, monkeypatch):
        monkeypatch.setenv("CLAUDE_MODEL_GENERATE", "opus")
        assert get_model("generate") == "opus"

    def test_override_iterate_model(self, monkeypatch):
        monkeypatch.setenv("CLAUDE_MODEL_ITERATE", "haiku")
        assert get_model("iterate") == "haiku"

    def test_override_classify_model(self, monkeypatch):
        monkeypatch.setenv("CLAUDE_MODEL_CLASSIFY", "sonnet")
        assert get_model("classify") == "sonnet"

    def test_override_calendar_model(self, monkeypatch):
        monkeypatch.setenv("CLAUDE_MODEL_CALENDAR", "opus")
        assert get_model("calendar") == "opus"

    def test_override_suggest_model(self, monkeypatch):
        monkeypatch.setenv("CLAUDE_MODEL_SUGGEST", "haiku")
        assert get_model("suggest") == "haiku"


class TestUnknownTaskType:
    def test_unknown_task_falls_back_to_sonnet(self):
        assert get_model("unknown_task") == "sonnet"

    def test_empty_string_falls_back_to_sonnet(self):
        assert get_model("") == "sonnet"
