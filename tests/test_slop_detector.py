"""Tests for AI slop detection module."""

import pytest

from content_engine.slop_detector import SlopDetector, SlopResult


@pytest.fixture
def detector():
    return SlopDetector()


class TestSlopResult:
    def test_is_slop_above_threshold(self):
        r = SlopResult(score=0.4, matches=["test"], suggestions=[])
        assert r.is_slop(threshold=0.3)

    def test_not_slop_below_threshold(self):
        r = SlopResult(score=0.1, matches=["test"], suggestions=[])
        assert not r.is_slop(threshold=0.3)


class TestPatternLoading:
    def test_loads_patterns(self, detector):
        assert len(detector.patterns) > 0

    def test_has_ai_cliches(self, detector):
        categories = {p.category for p in detector.patterns}
        assert "ai_cliches" in categories

    def test_has_antipatterns(self, detector):
        categories = {p.category for p in detector.patterns}
        assert "gita_valley_antipatterns" in categories


class TestAIClicheDetection:
    def test_detects_hearts_overflowing(self, detector):
        result = detector.detect("Our hearts are overflowing with gratitude")
        assert result.score > 0
        assert any("hearts" in m.lower() and "overflowing" in m.lower() for m in result.matches)

    def test_detects_nestled(self, detector):
        result = detector.detect("Nestled in the rolling hills of PA")
        assert result.score > 0

    def test_detects_tapestry(self, detector):
        result = detector.detect("A rich tapestry of farm life and spirituality")
        assert result.score > 0

    def test_detects_journey(self, detector):
        result = detector.detect("Join us on this incredible journey")
        assert result.score > 0

    def test_detects_game_changer(self, detector):
        result = detector.detect("This is a real game-changer for farming")
        assert result.score > 0

    def test_detects_lets_dive_in(self, detector):
        result = detector.detect("Let's dive in to what makes our farm special")
        assert result.score > 0


class TestGitaValleyAntipatterns:
    def test_detects_sacred_bovine(self, detector):
        result = detector.detect("Our sacred bovine companions graze freely")
        assert result.score > 0

    def test_detects_spiritual_awakening(self, detector):
        result = detector.detect("Experience spiritual awakening at the farm")
        assert result.score > 0

    def test_detects_transcendent(self, detector):
        result = detector.detect("A transcendent experience awaits you at Gita Valley")
        assert result.score > 0


class TestFillerDetection:
    def test_detects_at_the_end_of_the_day(self, detector):
        result = detector.detect("At the end of the day, it's about the cows")
        assert result.score > 0

    def test_detects_needless_to_say(self, detector):
        result = detector.detect("Needless to say, our cows are well cared for")
        assert result.score > 0


class TestScoring:
    def test_score_zero_for_clean_text(self, detector):
        result = detector.detect("Nandini had a great morning in the field.")
        assert result.score == 0.0
        assert result.matches == []

    def test_score_increases_with_more_matches(self, detector):
        low = detector.detect("Our hearts overflowing with joy")
        high = detector.detect(
            "Our hearts overflowing with joy on this incredible journey "
            "through the tapestry of farm life"
        )
        assert high.score > low.score

    def test_score_capped_at_one(self, detector):
        text = (
            "Let's dive in to this incredible journey through the "
            "tapestry of our sacred bovine sanctuary. Nestled in the "
            "rolling hills, our hearts overflowing with every life being "
            "a blessing. At the end of the day, needless to say, this "
            "game-changer is a symphony of grace."
        )
        result = detector.detect(text)
        assert result.score <= 1.0

    def test_antipatterns_weight_more(self, detector):
        # Antipattern (0.2 each) should score higher than filler (0.1)
        anti = detector.detect("sacred bovine companions")
        filler = detector.detect("at the end of the day")
        assert anti.score >= filler.score


class TestCaseInsensitive:
    def test_matches_uppercase(self, detector):
        result = detector.detect("HEARTS OVERFLOWING with gratitude")
        assert result.score > 0

    def test_matches_mixed_case(self, detector):
        result = detector.detect("Nestled In The Hills")
        assert result.score > 0


class TestKnownGoodPosts:
    """Real Gita Valley posts should NOT trigger slop detection."""

    def test_cow_portrait(self, detector):
        result = detector.detect(
            "Nandini is a cow who requires extra care due to her disability. "
            "She loves morning walks and fresh hay."
        )
        assert result.score < 0.3

    def test_scenic_caption(self, detector):
        result = detector.detect("Early morning in Gita Valley")
        assert result.score == 0.0

    def test_event_invitation(self, detector):
        result = detector.detect(
            "We would love for you to join in on the country style Chariot Festival!"
        )
        assert result.score == 0.0

    def test_product_mention(self, detector):
        result = detector.detect(
            "Fresh paneer from our Happy Cows. We grow the hay, love the cows."
        )
        assert result.score == 0.0
