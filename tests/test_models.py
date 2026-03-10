"""Tests for Pydantic data models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from content_engine.models import (
    ContentPillar,
    ContentRow,
    ContentStatus,
    LearningContext,
    Platform,
    PostPerformance,
    Suggestion,
)


class TestEnums:
    def test_content_status_values(self) -> None:
        assert ContentStatus.DRAFT == "draft"
        assert ContentStatus.READY == "ready"
        assert ContentStatus.PENDING_APPROVAL == "pending_approval"
        assert ContentStatus.APPROVED == "approved"
        assert ContentStatus.POSTED == "posted"
        assert ContentStatus.ERROR == "error"

    def test_content_pillar_values(self) -> None:
        assert ContentPillar.COW_LIFE == "Cow Life"
        assert ContentPillar.FARM_OPS == "Farm Ops"
        assert ContentPillar.COMMUNITY == "Community"
        assert ContentPillar.KITCHEN == "Kitchen"
        assert ContentPillar.SPIRITUAL == "Spiritual"
        assert ContentPillar.CTA == "CTA"

    def test_platform_values(self) -> None:
        assert Platform.INSTAGRAM == "instagram"
        assert Platform.FACEBOOK == "facebook"
        assert Platform.TIKTOK == "tiktok"
        assert Platform.THREADS == "threads"
        assert Platform.LINKEDIN == "linkedin"


class TestContentRow:
    def test_valid_content_row(self) -> None:
        row = ContentRow(
            row_number=1,
            date=datetime(2026, 3, 1, 10, 0),
            content_pillar=ContentPillar.COW_LIFE,
            raw_text="Baby calf born this morning!",
            media_url="https://drive.google.com/file/d/abc123",
            platforms={Platform.INSTAGRAM: True, Platform.FACEBOOK: True},
            status=ContentStatus.READY,
            captions={},
        )
        assert row.row_number == 1
        assert row.raw_text == "Baby calf born this morning!"
        assert row.source == "staff"

    def test_content_row_minimal(self) -> None:
        """Minimal required fields only."""
        row = ContentRow(
            row_number=2,
            date=datetime(2026, 3, 1),
            raw_text="Farm update",
            platforms={},
            status=ContentStatus.DRAFT,
            captions={},
        )
        assert row.content_pillar is None
        assert row.media_url is None
        assert row.feedback is None
        assert row.postiz_ids is None

    def test_content_row_invalid_status(self) -> None:
        with pytest.raises(ValidationError):
            ContentRow(
                row_number=1,
                date=datetime(2026, 3, 1),
                raw_text="Test",
                platforms={},
                status="invalid_status",
                captions={},
            )

    def test_content_row_invalid_media_url(self) -> None:
        with pytest.raises(ValidationError):
            ContentRow(
                row_number=1,
                date=datetime(2026, 3, 1),
                raw_text="Test",
                platforms={},
                status=ContentStatus.DRAFT,
                captions={},
                media_url="not-a-url",
            )

    def test_content_row_with_captions(self) -> None:
        row = ContentRow(
            row_number=1,
            date=datetime(2026, 3, 1),
            raw_text="Farm event",
            platforms={Platform.INSTAGRAM: True},
            status=ContentStatus.PENDING_APPROVAL,
            captions={Platform.INSTAGRAM: "Check out our spring festival!"},
        )
        assert row.captions[Platform.INSTAGRAM] == "Check out our spring festival!"


class TestSuggestion:
    def test_valid_suggestion(self) -> None:
        s = Suggestion(
            suggested_date=datetime(2026, 3, 15),
            content_idea="Spring planting photo series",
            suggested_pillar=ContentPillar.FARM_OPS,
            rationale="Spring content performs 2x better historically",
            media_suggestion="Photos of seedlings being planted",
        )
        assert s.status == "suggested"

    def test_suggestion_requires_all_fields(self) -> None:
        with pytest.raises(ValidationError):
            Suggestion(
                suggested_date=datetime(2026, 3, 15),
                content_idea="Missing fields",
            )


class TestPostPerformance:
    def test_valid_performance(self) -> None:
        p = PostPerformance(
            post_id="post_123",
            platform=Platform.INSTAGRAM,
            pillar=ContentPillar.COW_LIFE,
            posted_at=datetime(2026, 2, 20, 14, 0),
            likes=150,
            comments=23,
            shares=8,
            reach=2500,
            engagement_rate=7.24,
        )
        assert p.engagement_rate == 7.24

    def test_performance_defaults(self) -> None:
        p = PostPerformance(
            post_id="post_456",
            platform=Platform.FACEBOOK,
            pillar=ContentPillar.SPIRITUAL,
            posted_at=datetime(2026, 2, 20),
        )
        assert p.likes == 0
        assert p.engagement_rate == 0.0


class TestLearningContext:
    def test_valid_learning_context(self) -> None:
        ctx = LearningContext(
            last_updated=datetime(2026, 2, 24),
            top_performing_pillars=["Cow Life", "Kitchen"],
            best_posting_times={"instagram": ["10:00", "18:00"]},
            hashtag_performance={"#farmlife": 5.2, "#iskcon": 3.1},
            pillar_distribution={"Cow Life": 0.35, "Spiritual": 0.25},
            insights=["Cow content peaks on weekends"],
        )
        assert len(ctx.top_performing_pillars) == 2
        assert ctx.insights[0] == "Cow content peaks on weekends"
