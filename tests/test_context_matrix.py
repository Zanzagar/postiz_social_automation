"""Tests for context injection matrix."""


from content_engine.context_matrix import CONTEXT_MATRIX, build_context


class TestContextMatrix:
    def test_generate_includes_knowledge(self):
        assert "knowledge" in CONTEXT_MATRIX["generate"]

    def test_generate_includes_few_shots(self):
        assert "few_shots" in CONTEXT_MATRIX["generate"]

    def test_iterate_excludes_knowledge(self):
        assert "knowledge" not in CONTEXT_MATRIX["iterate"]

    def test_iterate_includes_brand_voice(self):
        assert "brand_voice" in CONTEXT_MATRIX["iterate"]

    def test_calendar_includes_festivals(self):
        assert "festivals" in CONTEXT_MATRIX["calendar"]

    def test_suggest_includes_festivals(self):
        assert "festivals" in CONTEXT_MATRIX["suggest"]


class TestBuildContext:
    def test_generate_context(self):
        ctx = build_context(
            "generate",
            brand_voice="Gita Valley brand",
            learned_rules=["rule1"],
            knowledge="80 cows",
            few_shots=[{"caption": "test"}],
            festivals=[{"name": "Rama Navami"}],
        )
        assert ctx["brand_voice"] == "Gita Valley brand"
        assert ctx["knowledge"] == "80 cows"
        assert "festivals" not in ctx  # Not in generate matrix

    def test_iterate_context(self):
        ctx = build_context(
            "iterate",
            brand_voice="voice",
            learned_rules=["rule"],
            knowledge="should be excluded",
            few_shots=[{"caption": "test"}],
        )
        assert ctx["brand_voice"] == "voice"
        assert "knowledge" not in ctx

    def test_calendar_context(self):
        ctx = build_context(
            "calendar",
            brand_voice="voice",
            knowledge="facts",
            festivals=[{"name": "Diwali"}],
        )
        assert ctx["festivals"] == [{"name": "Diwali"}]
        assert ctx["knowledge"] == "facts"

    def test_unknown_endpoint_returns_minimal(self):
        ctx = build_context(
            "unknown",
            brand_voice="voice",
            knowledge="facts",
        )
        # Should return brand_voice at minimum (always included)
        assert ctx.get("brand_voice") == "voice"

    def test_missing_kwargs_excluded(self):
        ctx = build_context("generate", brand_voice="voice")
        assert "knowledge" not in ctx
        assert ctx["brand_voice"] == "voice"

    def test_none_values_excluded(self):
        ctx = build_context(
            "generate",
            brand_voice="voice",
            knowledge=None,
        )
        assert "knowledge" not in ctx
