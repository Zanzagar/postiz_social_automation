"""Testable helpers for the Performance Dashboard page."""

import json
from pathlib import Path

from content_engine.intelligence import TARGET_PILLAR_WEIGHTS


def load_dashboard_data(*, data_dir: Path) -> dict:
    """Load the learning context JSON file."""
    path = data_dir / "learning-context.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def load_performance_posts(*, data_dir: Path) -> list[dict]:
    """Load the post performance data."""
    path = data_dir / "post-performance.json"
    if not path.exists():
        return []
    return json.loads(path.read_text())


def compute_metrics(posts: list[dict]) -> dict:
    """Compute dashboard metrics from raw post data."""
    if not posts:
        return {
            "avg_engagement": 0.0,
            "total_posts": 0,
            "total_reach": 0,
        }

    rates = [p.get("engagement_rate", 0.0) for p in posts]
    return {
        "avg_engagement": sum(rates) / len(rates),
        "total_posts": len(posts),
        "total_reach": sum(p.get("reach", 0) for p in posts),
    }


def build_pillar_comparison(actual_distribution: dict[str, float]) -> list[dict]:
    """Build target vs actual pillar comparison data for charting.

    Returns list of dicts: [{"pillar": str, "target": float, "actual": float}, ...]
    Percentages are expressed as 0-100 (not 0-1).
    """
    result = []
    for pillar, target_pct in TARGET_PILLAR_WEIGHTS.items():
        actual_pct = actual_distribution.get(pillar, 0.0)
        result.append(
            {
                "pillar": pillar,
                "target": round(target_pct * 100, 1),
                "actual": round(actual_pct * 100, 1),
            }
        )
    return result
