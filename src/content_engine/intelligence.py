"""Content intelligence — calendar gaps, pillar balance, and learning context."""

import json
import logging
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from content_engine.models import ContentPillar
from content_engine.postiz import PostizClient
from content_engine.sheets import SheetsClient

logger = logging.getLogger(__name__)

TARGET_PILLAR_WEIGHTS: dict[ContentPillar, float] = {
    ContentPillar.COW_LIFE: 0.40,
    ContentPillar.FARM_OPS: 0.25,
    ContentPillar.COMMUNITY: 0.15,
    ContentPillar.KITCHEN: 0.10,
    ContentPillar.SPIRITUAL: 0.05,
    ContentPillar.CTA: 0.05,
}


class ContentIntelligence:
    """Analyzes content gaps, pillar balance, and builds learning context."""

    def __init__(
        self,
        sheets: SheetsClient,
        postiz: PostizClient,
        data_dir: Path = Path("data"),
    ) -> None:
        self.sheets = sheets
        self.postiz = postiz
        self.data_dir = data_dir

    def analyze_calendar_gaps(self, days_ahead: int = 14) -> list[dict]:
        """Find days with no scheduled content in the upcoming window.

        Returns list of dicts with 'date' (YYYY-MM-DD string) for each gap day.
        """
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        all_rows = self.sheets.get_all_content_rows()

        # Collect dates that have content
        covered_dates: set[str] = set()
        for row in all_rows:
            row_date = row.date.strftime("%Y-%m-%d")
            covered_dates.add(row_date)

        gaps = []
        for i in range(days_ahead):
            day = today + timedelta(days=i)
            day_str = day.strftime("%Y-%m-%d")
            if day_str not in covered_dates:
                gaps.append({"date": day_str})

        return gaps

    def analyze_pillar_balance(self, days_back: int = 30) -> dict[ContentPillar, dict]:
        """Compare actual pillar distribution to targets over recent period.

        Returns dict mapping each pillar to {'actual': float, 'target': float, 'deviation': float}.
        """
        cutoff = datetime.now() - timedelta(days=days_back)
        all_rows = self.sheets.get_all_content_rows()

        # Filter to recent posts with a pillar
        recent = [r for r in all_rows if r.date >= cutoff and r.content_pillar]
        total = len(recent)

        counts: Counter = Counter()
        for row in recent:
            counts[row.content_pillar] += 1

        result = {}
        for pillar in ContentPillar:
            actual = counts[pillar] / total if total > 0 else 0.0
            target = TARGET_PILLAR_WEIGHTS[pillar]
            result[pillar] = {
                "actual": round(actual, 2),
                "target": target,
                "deviation": round(actual - target, 2),
            }

        return result

    def get_upcoming_events(
        self,
        days_ahead: int = 7,
        reference_date: datetime | None = None,
    ) -> list[dict]:
        """Check festival calendar for upcoming events.

        Args:
            days_ahead: How many days ahead to look.
            reference_date: Fixed date for testing. Defaults to now.
        """
        festivals_path = self.data_dir / "festivals.json"
        if not festivals_path.exists():
            return []

        data = json.loads(festivals_path.read_text())
        festivals = data.get("festivals", [])

        ref = reference_date or datetime.now()
        ref = ref.replace(hour=0, minute=0, second=0, microsecond=0)
        end = ref + timedelta(days=days_ahead)

        upcoming = []
        for fest in festivals:
            date_str = fest.get("date")
            if not date_str:
                continue  # Skip recurring events without fixed date
            try:
                fest_date = datetime.fromisoformat(date_str)
                if ref <= fest_date < end:
                    upcoming.append(
                        {
                            "name": fest["name"],
                            "date": date_str,
                            "description": fest.get("description", ""),
                        }
                    )
            except ValueError:
                logger.warning("Invalid date in festivals.json: %s", date_str)

        return upcoming

    def build_learning_context(self) -> dict:
        """Compile performance data into learning context for AI prompts."""
        performance_path = self.data_dir / "post-performance.json"
        if not performance_path.exists():
            return {
                "last_updated": datetime.now().isoformat(),
                "insights": [],
            }

        posts = json.loads(performance_path.read_text())

        return {
            "last_updated": datetime.now().isoformat(),
            "top_performing_pillars": self._rank_pillars(posts),
            "best_posting_times": self._analyze_timing(posts),
            "pillar_distribution": self._calculate_distribution(posts),
            "insights": self._generate_insights(posts),
        }

    def save_learning_context(self) -> None:
        """Update data/learning-context.json with latest analysis."""
        context = self.build_learning_context()
        path = self.data_dir / "learning-context.json"
        path.write_text(json.dumps(context, indent=2))
        logger.info("Saved learning context to %s", path)

    def _rank_pillars(self, posts: list[dict]) -> list[str]:
        """Rank pillars by average engagement rate."""
        pillar_engagement: dict[str, list[float]] = {}
        for post in posts:
            pillar = post.get("pillar", "Unknown")
            rate = post.get("engagement_rate", 0.0)
            pillar_engagement.setdefault(pillar, []).append(rate)

        avg_engagement = {p: sum(rates) / len(rates) for p, rates in pillar_engagement.items()}
        return sorted(avg_engagement, key=avg_engagement.get, reverse=True)

    def _analyze_timing(self, posts: list[dict]) -> dict[str, list[str]]:
        """Find best posting times per platform."""
        platform_times: dict[str, list[tuple[str, float]]] = {}
        for post in posts:
            platform = post.get("platform", "unknown")
            posted_at = post.get("posted_at", "")
            rate = post.get("engagement_rate", 0.0)
            if posted_at:
                try:
                    hour = datetime.fromisoformat(posted_at).strftime("%H:00")
                    platform_times.setdefault(platform, []).append((hour, rate))
                except ValueError:
                    pass

        best_times: dict[str, list[str]] = {}
        for platform, times in platform_times.items():
            # Group by hour, find top 3
            hour_rates: dict[str, list[float]] = {}
            for hour, rate in times:
                hour_rates.setdefault(hour, []).append(rate)
            avg_by_hour = {h: sum(r) / len(r) for h, r in hour_rates.items()}
            sorted_hours = sorted(avg_by_hour, key=avg_by_hour.get, reverse=True)
            best_times[platform] = sorted_hours[:3]

        return best_times

    def _calculate_distribution(self, posts: list[dict]) -> dict[str, float]:
        """Calculate actual pillar distribution from performance data."""
        total = len(posts)
        if total == 0:
            return {}

        counts: Counter = Counter(post.get("pillar", "Unknown") for post in posts)
        return {pillar: round(count / total, 2) for pillar, count in counts.items()}

    def _generate_insights(self, posts: list[dict]) -> list[str]:
        """Generate simple text insights from performance data."""
        if not posts:
            return []

        insights = []

        # Top performing pillar
        ranked = self._rank_pillars(posts)
        if ranked:
            insights.append(f"Top performing content pillar: {ranked[0]}")

        # Average engagement
        rates = [p.get("engagement_rate", 0.0) for p in posts]
        avg_rate = sum(rates) / len(rates) if rates else 0
        insights.append(f"Average engagement rate: {avg_rate:.1%}")

        # Total reach
        total_reach = sum(p.get("reach", 0) for p in posts)
        insights.append(f"Total reach across {len(posts)} posts: {total_reach:,}")

        return insights
