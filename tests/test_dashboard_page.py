"""Tests for the Performance Dashboard page (Task 14).

Tests verify:
- Page file exists
- Dashboard helpers load and parse performance data
- Metrics are computed correctly from raw data
- Handles missing/empty data gracefully
"""

import json
from pathlib import Path

from content_engine.intelligence import TARGET_PILLAR_WEIGHTS


class TestDashboardPageExists:
    def test_page_file_exists(self) -> None:
        page = Path("app/pages/3_Analytics.py")
        assert page.exists(), f"Analytics/Dashboard page not found at {page}"


class TestLoadDashboardData:
    def test_loads_learning_context(self, tmp_path: Path) -> None:
        from app.helpers.dashboard_helpers import load_dashboard_data

        context_file = tmp_path / "learning-context.json"
        context_file.write_text(
            json.dumps(
                {
                    "last_updated": "2026-02-24T12:00:00",
                    "top_performing_pillars": ["Cow Life", "Farm Ops"],
                    "best_posting_times": {"instagram": ["09:00", "18:00"]},
                    "pillar_distribution": {"Cow Life": 0.35, "Farm Ops": 0.25},
                    "insights": ["Top performing content pillar: Cow Life"],
                }
            )
        )

        data = load_dashboard_data(data_dir=tmp_path)
        assert data["last_updated"] == "2026-02-24T12:00:00"
        assert "Cow Life" in data["top_performing_pillars"]

    def test_returns_empty_when_no_file(self, tmp_path: Path) -> None:
        from app.helpers.dashboard_helpers import load_dashboard_data

        data = load_dashboard_data(data_dir=tmp_path)
        assert data == {}

    def test_loads_performance_posts(self, tmp_path: Path) -> None:
        from app.helpers.dashboard_helpers import load_performance_posts

        perf_file = tmp_path / "post-performance.json"
        perf_file.write_text(
            json.dumps(
                [
                    {
                        "post_id": "p1",
                        "platform": "instagram",
                        "likes": 50,
                        "engagement_rate": 0.05,
                    },
                    {"post_id": "p2", "platform": "facebook", "likes": 30, "engagement_rate": 0.03},
                ]
            )
        )

        posts = load_performance_posts(data_dir=tmp_path)
        assert len(posts) == 2
        assert posts[0]["post_id"] == "p1"

    def test_returns_empty_list_when_no_performance_file(self, tmp_path: Path) -> None:
        from app.helpers.dashboard_helpers import load_performance_posts

        posts = load_performance_posts(data_dir=tmp_path)
        assert posts == []


class TestComputeMetrics:
    def test_computes_avg_engagement(self) -> None:
        from app.helpers.dashboard_helpers import compute_metrics

        posts = [
            {"engagement_rate": 0.05},
            {"engagement_rate": 0.03},
            {"engagement_rate": 0.07},
        ]
        metrics = compute_metrics(posts)
        assert abs(metrics["avg_engagement"] - 0.05) < 0.001

    def test_handles_empty_posts(self) -> None:
        from app.helpers.dashboard_helpers import compute_metrics

        metrics = compute_metrics([])
        assert metrics["avg_engagement"] == 0.0
        assert metrics["total_posts"] == 0

    def test_counts_total_posts(self) -> None:
        from app.helpers.dashboard_helpers import compute_metrics

        posts = [{"engagement_rate": 0.01} for _ in range(5)]
        metrics = compute_metrics(posts)
        assert metrics["total_posts"] == 5

    def test_computes_total_reach(self) -> None:
        from app.helpers.dashboard_helpers import compute_metrics

        posts = [
            {"engagement_rate": 0.01, "reach": 100},
            {"engagement_rate": 0.02, "reach": 200},
        ]
        metrics = compute_metrics(posts)
        assert metrics["total_reach"] == 300


class TestBuildPillarChart:
    def test_builds_target_vs_actual(self) -> None:
        from app.helpers.dashboard_helpers import build_pillar_comparison

        actual = {"Cow Life": 0.35, "Farm Ops": 0.20}
        result = build_pillar_comparison(actual)
        assert len(result) == len(TARGET_PILLAR_WEIGHTS)
        cow_row = [r for r in result if r["pillar"] == "Cow Life"][0]
        assert cow_row["actual"] == 35.0
        assert cow_row["target"] == 40.0

    def test_handles_missing_pillars(self) -> None:
        from app.helpers.dashboard_helpers import build_pillar_comparison

        result = build_pillar_comparison({})
        assert len(result) == len(TARGET_PILLAR_WEIGHTS)
        for row in result:
            assert row["actual"] == 0.0
