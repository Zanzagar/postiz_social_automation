"""Tests for Content Intelligence module (Task 15)."""

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from content_engine.models import ContentPillar, ContentRow, ContentStatus, Platform


def _make_posted_row(
    row_number: int,
    pillar: ContentPillar,
    date: datetime,
) -> ContentRow:
    """Helper for a posted ContentRow."""
    return ContentRow(
        row_number=row_number,
        date=date,
        content_pillar=pillar,
        raw_text="Test content",
        platforms={Platform.INSTAGRAM: True},
        status=ContentStatus.POSTED,
        captions={Platform.INSTAGRAM: "caption"},
    )


class TestTargetWeights:
    """Verify target pillar weights match content strategy."""

    def test_weights_sum_to_one(self):
        from content_engine.intelligence import TARGET_PILLAR_WEIGHTS

        total = sum(TARGET_PILLAR_WEIGHTS.values())
        assert abs(total - 1.0) < 0.01

    def test_cow_life_is_largest(self):
        from content_engine.intelligence import TARGET_PILLAR_WEIGHTS

        assert TARGET_PILLAR_WEIGHTS[ContentPillar.COW_LIFE] == 0.40

    def test_all_pillars_present(self):
        from content_engine.intelligence import TARGET_PILLAR_WEIGHTS

        for pillar in ContentPillar:
            assert pillar in TARGET_PILLAR_WEIGHTS


class TestCalendarGapAnalysis:
    """Test analyze_calendar_gaps finds days with no content."""

    def test_finds_gap_days(self, tmp_path):
        from content_engine.intelligence import ContentIntelligence

        sheets = MagicMock()
        postiz = MagicMock()

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Content on day 1 and 3, gap on day 2
        sheets.get_all_content_rows.return_value = [
            _make_posted_row(2, ContentPillar.COW_LIFE, today + timedelta(days=1)),
            _make_posted_row(3, ContentPillar.FARM_OPS, today + timedelta(days=3)),
        ]

        intel = ContentIntelligence(sheets=sheets, postiz=postiz, data_dir=tmp_path)
        gaps = intel.analyze_calendar_gaps(days_ahead=4)

        # Today, day 2, and day 4 should be gaps
        gap_dates = [g["date"] for g in gaps]
        assert (today + timedelta(days=2)).strftime("%Y-%m-%d") in gap_dates

    def test_no_gaps_when_all_days_covered(self, tmp_path):
        from content_engine.intelligence import ContentIntelligence

        sheets = MagicMock()
        postiz = MagicMock()

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Content every day for 3 days
        sheets.get_all_content_rows.return_value = [
            _make_posted_row(i, ContentPillar.COW_LIFE, today + timedelta(days=i)) for i in range(3)
        ]

        intel = ContentIntelligence(sheets=sheets, postiz=postiz, data_dir=tmp_path)
        gaps = intel.analyze_calendar_gaps(days_ahead=3)
        assert len(gaps) == 0

    def test_empty_calendar_all_gaps(self, tmp_path):
        from content_engine.intelligence import ContentIntelligence

        sheets = MagicMock()
        postiz = MagicMock()
        sheets.get_all_content_rows.return_value = []

        intel = ContentIntelligence(sheets=sheets, postiz=postiz, data_dir=tmp_path)
        gaps = intel.analyze_calendar_gaps(days_ahead=7)
        assert len(gaps) == 7


class TestPillarBalance:
    """Test analyze_pillar_balance compares actual to targets."""

    def test_balanced_distribution(self, tmp_path):
        from content_engine.intelligence import ContentIntelligence

        sheets = MagicMock()
        postiz = MagicMock()

        today = datetime.now()
        # 10 posts: 4 cow, 2 farm, 2 community, 1 kitchen, 1 spiritual
        rows = (
            [
                _make_posted_row(i, ContentPillar.COW_LIFE, today - timedelta(days=i))
                for i in range(4)
            ]
            + [
                _make_posted_row(10 + i, ContentPillar.FARM_OPS, today - timedelta(days=i))
                for i in range(2)
            ]
            + [
                _make_posted_row(20 + i, ContentPillar.COMMUNITY, today - timedelta(days=i))
                for i in range(2)
            ]
            + [_make_posted_row(30, ContentPillar.KITCHEN, today)]
            + [_make_posted_row(31, ContentPillar.SPIRITUAL, today)]
        )

        sheets.get_all_content_rows.return_value = rows

        intel = ContentIntelligence(sheets=sheets, postiz=postiz, data_dir=tmp_path)
        balance = intel.analyze_pillar_balance(days_back=30)

        # Should return actual distribution
        assert ContentPillar.COW_LIFE in balance
        assert balance[ContentPillar.COW_LIFE]["actual"] == 0.4  # 4/10

    def test_empty_calendar_returns_zeros(self, tmp_path):
        from content_engine.intelligence import ContentIntelligence

        sheets = MagicMock()
        postiz = MagicMock()
        sheets.get_all_content_rows.return_value = []

        intel = ContentIntelligence(sheets=sheets, postiz=postiz, data_dir=tmp_path)
        balance = intel.analyze_pillar_balance(days_back=30)

        for pillar in ContentPillar:
            assert balance[pillar]["actual"] == 0.0


class TestUpcomingEvents:
    """Test festival calendar lookup."""

    def test_finds_upcoming_festivals(self, tmp_path):
        from content_engine.intelligence import ContentIntelligence

        # Write test festival data
        festivals = {
            "festivals": [
                {"name": "Test Festival", "date": "2026-03-07", "description": "Test event"},
                {"name": "Far Away", "date": "2026-12-25", "description": "Too far"},
            ]
        }
        (tmp_path / "festivals.json").write_text(json.dumps(festivals))

        sheets = MagicMock()
        postiz = MagicMock()

        intel = ContentIntelligence(sheets=sheets, postiz=postiz, data_dir=tmp_path)
        # Use a fixed reference date for deterministic testing
        events = intel.get_upcoming_events(days_ahead=14, reference_date=datetime(2026, 3, 1))

        assert len(events) == 1
        assert events[0]["name"] == "Test Festival"

    def test_no_upcoming_events(self, tmp_path):
        from content_engine.intelligence import ContentIntelligence

        festivals = {
            "festivals": [{"name": "Past Event", "date": "2025-01-01", "description": "Old"}]
        }
        (tmp_path / "festivals.json").write_text(json.dumps(festivals))

        sheets = MagicMock()
        postiz = MagicMock()

        intel = ContentIntelligence(sheets=sheets, postiz=postiz, data_dir=tmp_path)
        events = intel.get_upcoming_events(days_ahead=7, reference_date=datetime(2026, 3, 1))
        assert events == []

    def test_handles_missing_festival_file(self, tmp_path):
        from content_engine.intelligence import ContentIntelligence

        sheets = MagicMock()
        postiz = MagicMock()

        intel = ContentIntelligence(sheets=sheets, postiz=postiz, data_dir=tmp_path)
        events = intel.get_upcoming_events(days_ahead=7)
        assert events == []


class TestBuildLearningContext:
    """Test learning context compilation."""

    def test_builds_context_with_performance_data(self, tmp_path):
        from content_engine.intelligence import ContentIntelligence

        # Write sample performance data
        perf_data = [
            {
                "post_id": "p1",
                "platform": "instagram",
                "pillar": "Cow Life",
                "posted_at": "2026-02-20T10:00:00",
                "likes": 50,
                "comments": 10,
                "shares": 5,
                "reach": 500,
                "engagement_rate": 0.13,
            },
            {
                "post_id": "p2",
                "platform": "facebook",
                "pillar": "Farm Ops",
                "posted_at": "2026-02-21T14:00:00",
                "likes": 20,
                "comments": 3,
                "shares": 1,
                "reach": 200,
                "engagement_rate": 0.12,
            },
        ]
        (tmp_path / "post-performance.json").write_text(json.dumps(perf_data))

        sheets = MagicMock()
        postiz = MagicMock()

        intel = ContentIntelligence(sheets=sheets, postiz=postiz, data_dir=tmp_path)
        context = intel.build_learning_context()

        assert "last_updated" in context
        assert "top_performing_pillars" in context
        assert "pillar_distribution" in context
        assert isinstance(context["top_performing_pillars"], list)

    def test_empty_performance_returns_defaults(self, tmp_path):
        from content_engine.intelligence import ContentIntelligence

        sheets = MagicMock()
        postiz = MagicMock()

        intel = ContentIntelligence(sheets=sheets, postiz=postiz, data_dir=tmp_path)
        context = intel.build_learning_context()

        assert "last_updated" in context
        assert context.get("insights") == []

    def test_save_learning_context_writes_file(self, tmp_path):
        from content_engine.intelligence import ContentIntelligence

        sheets = MagicMock()
        postiz = MagicMock()

        intel = ContentIntelligence(sheets=sheets, postiz=postiz, data_dir=tmp_path)
        intel.save_learning_context()

        output = tmp_path / "learning-context.json"
        assert output.exists()
        data = json.loads(output.read_text())
        assert "last_updated" in data
