"""Tests for the unified analytics query layer (content_engine.analytics.unified).

All clock-dependent tests inject a fixed `now` — never wall-clock.
"""

import json
import sqlite3
from datetime import datetime

import pytest

from content_engine.analytics import unified
from content_engine.analytics.unified import (
    PlatformRecord,
    aggregate_posts,
    compute_heatmap,
    compute_pillar_insights,
    compute_summary_insights,
    hour_bucket,
    parse_dt,
    previous_window_dates,
    resolve_range,
    window_dates,
)

FROZEN_NOW = datetime(2026, 7, 14, 12, 0, 0)  # naive UTC


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


SCHEMA = """
    CREATE TABLE content_rows (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date DATETIME,
        pillar TEXT,
        raw_text TEXT,
        platforms TEXT,
        status TEXT DEFAULT 'draft',
        postiz_ids TEXT,
        posted_at DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE analytics_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content_row_id INTEGER REFERENCES content_rows(id),
        platform TEXT NOT NULL,
        postiz_post_id TEXT,
        likes INTEGER DEFAULT 0,
        shares INTEGER DEFAULT 0,
        comments INTEGER DEFAULT 0,
        reach INTEGER DEFAULT 0,
        impressions INTEGER DEFAULT 0,
        fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE social_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT NOT NULL,
        external_id TEXT NOT NULL,
        post_text TEXT,
        media_urls TEXT,
        hashtags TEXT,
        posted_at DATETIME,
        likes INTEGER DEFAULT 0,
        comments INTEGER DEFAULT 0,
        shares INTEGER DEFAULT 0,
        reach INTEGER DEFAULT 0,
        pillar TEXT,
        imported_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(platform, external_id)
    );
    CREATE TABLE hashtag_performance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hashtag TEXT NOT NULL,
        platform TEXT NOT NULL,
        times_used INTEGER NOT NULL,
        total_engagement INTEGER NOT NULL,
        avg_engagement REAL NOT NULL,
        trend TEXT NOT NULL,
        updated_at DATETIME NOT NULL,
        UNIQUE(hashtag, platform)
    );
    CREATE TABLE pillars (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(100) UNIQUE NOT NULL,
        description TEXT,
        color VARCHAR(20),
        is_active BOOLEAN DEFAULT 1,
        sort_order INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        target_distribution FLOAT
    );
"""


@pytest.fixture
def empty_db(tmp_path):
    db_path = tmp_path / "empty.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    return str(db_path)


@pytest.fixture
def seeded_db(tmp_path):
    """Mixed app + history data around the frozen clock (2026-07-14)."""
    db_path = tmp_path / "seeded.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA)
    conn.executescript("""
        INSERT INTO pillars (name, color, target_distribution)
        VALUES ('Cow Life', '#16a34a', 0.4);
        INSERT INTO pillars (name, color, target_distribution)
        VALUES ('Community', '#7c3aed', 0.25);

        -- App post 1: two platforms, posted inside the 30d window
        INSERT INTO content_rows (id, date, pillar, raw_text, status, posted_at, created_at)
        VALUES (1, '2026-07-01 09:00:00', 'Cow Life', 'Our cows love sunrise', 'posted',
                '2026-07-01 09:00:00', '2026-06-28 09:00:00');
        INSERT INTO analytics_cache (content_row_id, platform, likes, comments,
                                     shares, reach, impressions)
        VALUES (1, 'instagram', 60, 10, 5, 500, 1200);
        INSERT INTO analytics_cache (content_row_id, platform, likes, comments,
                                     shares, reach, impressions)
        VALUES (1, 'facebook', 30, 5, 8, 300, 600);

        -- App post 2: inside window
        INSERT INTO content_rows (id, date, pillar, raw_text, status, posted_at, created_at)
        VALUES (2, '2026-07-08 15:30:00', 'Community', 'Sunday Feast this week', 'posted',
                '2026-07-08 15:30:00', '2026-07-07 10:00:00');
        INSERT INTO analytics_cache (content_row_id, platform, likes, comments,
                                     shares, reach, impressions)
        VALUES (2, 'instagram', 25, 3, 2, 200, 400);

        -- App post 3: in the PREVIOUS 30d window
        INSERT INTO content_rows (id, date, pillar, raw_text, status, posted_at, created_at)
        VALUES (3, '2026-05-20 12:00:00', 'Cow Life', 'New calves born today', 'posted',
                '2026-05-20 12:00:00', '2026-05-19 12:00:00');
        INSERT INTO analytics_cache (content_row_id, platform, likes, comments,
                                     shares, reach, impressions)
        VALUES (3, 'instagram', 80, 15, 10, 700, 1500);

        -- History posts (Postiz-independent), inside window
        INSERT INTO social_history (platform, external_id, post_text, hashtags, posted_at,
                                    likes, comments, shares, reach, pillar)
        VALUES ('facebook', 'fb_1', 'Morning kirtan by the barn', '["GitaValley"]',
                '2026-07-07T18:30:00+0000', 40, 6, 4, 400, 'Community');
        INSERT INTO social_history (platform, external_id, post_text, hashtags, posted_at,
                                    likes, comments, shares, reach, pillar)
        VALUES ('facebook', 'fb_2', 'Hay harvest complete', '[]',
                '2026-07-10T09:15:00+0000', 20, 2, 2, 300, NULL);
        -- History post far outside any window
        INSERT INTO social_history (platform, external_id, post_text, hashtags, posted_at,
                                    likes, comments, shares, reach, pillar)
        VALUES ('facebook', 'fb_old', 'Old post', '[]',
                '2022-05-25T17:12:15+0000', 100, 10, 10, 1000, NULL);
    """)
    conn.commit()
    conn.close()
    return str(db_path)


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------


class TestParseDt:
    def test_parses_sqlite_space_format(self):
        assert parse_dt("2026-03-18 23:01:58.572527") == datetime(2026, 3, 18, 23, 1, 58, 572527)

    def test_parses_social_history_offset_format(self):
        dt = parse_dt("2022-05-25T17:12:15+0000")
        assert dt == datetime(2022, 5, 25, 17, 12, 15)
        assert dt.tzinfo is None

    def test_parses_zulu(self):
        assert parse_dt("2026-02-20T14:00:00Z") == datetime(2026, 2, 20, 14, 0, 0)

    def test_none_and_garbage(self):
        assert parse_dt(None) is None
        assert parse_dt("") is None
        assert parse_dt("not-a-date") is None


class TestWindows:
    def test_resolve_range(self):
        assert resolve_range("7d") == 7
        assert resolve_range("365d") == 365
        assert resolve_range(None) == 30
        assert resolve_range("bogus") == 30

    def test_window_dates_inclusive_days(self):
        start, end = window_dates(FROZEN_NOW, 7)
        assert end == FROZEN_NOW.date()
        assert (end - start).days == 6  # 7 calendar days inclusive

    def test_previous_window_abuts_current(self):
        cur_start, _ = window_dates(FROZEN_NOW, 30)
        prev_start, prev_end = previous_window_dates(FROZEN_NOW, 30)
        assert (cur_start - prev_end).days == 1
        assert (prev_end - prev_start).days == 29


class TestHourBucket:
    @pytest.mark.parametrize(
        "hour,expected",
        [
            (5, 0),
            (6, 0),
            (7, 0),  # 6a
            (8, 1),
            (9, 1),
            (10, 1),  # 9a
            (11, 2),
            (12, 2),
            (13, 2),  # 12p
            (14, 3),
            (15, 3),
            (16, 3),  # 3p
            (17, 4),
            (18, 4),
            (19, 4),  # 6p
            (20, 5),
            (21, 5),
            (22, 5),  # 9p
            (23, 5),  # outside → nearest (9p)
            (0, 0),
            (4, 0),  # outside → nearest (6a)
        ],
    )
    def test_bucket_mapping(self, hour, expected):
        assert hour_bucket(hour) == expected


class TestAggregatePosts:
    def test_app_records_merge_per_content_row(self):
        records = [
            PlatformRecord(
                1, "app", "text", "Cow Life", "instagram", datetime(2026, 7, 1), 60, 10, 5, 500
            ),
            PlatformRecord(
                1, "app", "text", "Cow Life", "facebook", datetime(2026, 7, 1), 30, 5, 8, 300
            ),
        ]
        posts = aggregate_posts(records)
        assert len(posts) == 1
        post = posts[0]
        assert sorted(post.platforms) == ["facebook", "instagram"]
        assert post.engagement == 118  # 75 + 43
        assert post.reach == 800
        assert post.top_platform == "instagram"  # 75 > 43

    def test_history_records_stay_individual(self):
        records = [
            PlatformRecord(1, "history", "a", None, "facebook", datetime(2026, 7, 1), 1, 0, 0, 10),
            PlatformRecord(2, "history", "b", None, "facebook", datetime(2026, 7, 2), 2, 0, 0, 10),
        ]
        posts = aggregate_posts(records)
        assert len(posts) == 2

    def test_rate_none_when_no_reach(self):
        records = [
            PlatformRecord(1, "history", "a", None, "facebook", datetime(2026, 7, 1), 5, 1, 0, 0),
        ]
        posts = aggregate_posts(records)
        assert posts[0].rate is None


class TestHeatmap:
    def test_empty_records_all_zeros_null_peak(self):
        result = compute_heatmap([])
        assert result["peak"] is None
        assert result["sample_size"] == 0
        assert len(result["days"]) == 7
        assert all(len(row) == 6 for row in result["days"])
        assert all(v == 0.0 for row in result["days"] for v in row)

    def test_peak_cell_normalized_to_one(self, monkeypatch):
        # Buckets are Eastern wall-clock (July = EDT, UTC-4):
        # Tue 2026-07-07 18:30 UTC = 14:30 ET (3p bucket);
        # Mon 2026-07-06 09:00 UTC = 05:00 ET (6a bucket).
        monkeypatch.setenv("GV_DISPLAY_TZ", "America/New_York")
        records = [
            PlatformRecord(
                1, "history", "", None, "facebook", datetime(2026, 7, 7, 18, 30), 90, 5, 5, 100
            ),
            PlatformRecord(
                2, "history", "", None, "facebook", datetime(2026, 7, 6, 9, 0), 10, 0, 0, 100
            ),
        ]
        result = compute_heatmap(records)
        assert result["sample_size"] == 2
        assert result["peak"] == {"day": 1, "bucket": 3}  # Tue, 3p ET
        assert result["days"][1][3] == 1.0
        assert result["days"][0][0] == pytest.approx(0.1)  # Mon 6a ET, 10/100

    def test_utc_evening_buckets_to_eastern_6p(self, monkeypatch):
        """23:30 UTC = 19:30 ET (EDT) → 6p bucket, same weekday."""
        monkeypatch.setenv("GV_DISPLAY_TZ", "America/New_York")
        records = [
            PlatformRecord(
                1, "history", "", None, "facebook", datetime(2026, 7, 7, 23, 30), 10, 0, 0, 100
            ),
        ]
        result = compute_heatmap(records)
        assert result["peak"] == {"day": 1, "bucket": 4}  # Tue, 6p ET

    def test_utc_early_morning_shifts_to_previous_eastern_weekday(self, monkeypatch):
        """Wed 02:30 UTC = Tue 22:30 ET → previous weekday, 9p bucket."""
        monkeypatch.setenv("GV_DISPLAY_TZ", "America/New_York")
        records = [
            PlatformRecord(
                1, "history", "", None, "facebook", datetime(2026, 7, 8, 2, 30), 10, 0, 0, 100
            ),
        ]
        result = compute_heatmap(records)
        assert result["peak"] == {"day": 1, "bucket": 5}  # Tue 9p ET, not Wed

    def test_display_tz_env_override(self, monkeypatch):
        """GV_DISPLAY_TZ=UTC keeps buckets in UTC wall-clock."""
        monkeypatch.setenv("GV_DISPLAY_TZ", "UTC")
        records = [
            PlatformRecord(
                1, "history", "", None, "facebook", datetime(2026, 7, 7, 18, 30), 10, 0, 0, 100
            ),
        ]
        result = compute_heatmap(records)
        assert result["peak"] == {"day": 1, "bucket": 4}  # Tue, 6p UTC

    def test_records_without_dates_excluded(self):
        records = [PlatformRecord(1, "history", "", None, "facebook", None, 9, 0, 0, 10)]
        result = compute_heatmap(records)
        assert result["sample_size"] == 0
        assert result["peak"] is None


# ---------------------------------------------------------------------------
# Insight rules
# ---------------------------------------------------------------------------


def _post(pillar, engagement, source="history"):
    from content_engine.analytics.unified import UnifiedPost

    return UnifiedPost(
        id=1,
        source=source,
        text="t",
        pillar=pillar,
        date=datetime(2026, 7, 1),
        likes=engagement,
    )


class TestSummaryInsights:
    def test_empty_below_five_posts(self):
        posts = [_post("Cow Life", 100) for _ in range(4)]
        assert compute_summary_insights(posts, []) == []

    def test_sage_when_pillar_outperforms_1_5x(self):
        posts = [_post("Cow Life", 300) for _ in range(3)] + [
            _post("Community", 50) for _ in range(3)
        ]
        insights = compute_summary_insights(posts, [])
        assert len(insights) == 1
        assert insights[0]["tone"] == "sage"
        assert "Cow Life" in insights[0]["title"]

    def test_no_sage_when_below_threshold(self):
        posts = [_post("Cow Life", 110) for _ in range(3)] + [
            _post("Community", 90) for _ in range(3)
        ]
        assert compute_summary_insights(posts, []) == []

    def test_terra_when_platform_rate_below_half(self):
        posts = [_post(None, 10) for _ in range(5)]
        records = [
            # instagram: 10% rate x3
            PlatformRecord(
                1, "history", "", None, "instagram", datetime(2026, 7, 1), 10, 0, 0, 100
            ),
            PlatformRecord(
                2, "history", "", None, "instagram", datetime(2026, 7, 1), 10, 0, 0, 100
            ),
            PlatformRecord(
                3, "history", "", None, "instagram", datetime(2026, 7, 1), 10, 0, 0, 100
            ),
            # facebook: 1% rate x3 (< half of overall avg)
            PlatformRecord(4, "history", "", None, "facebook", datetime(2026, 7, 1), 1, 0, 0, 100),
            PlatformRecord(5, "history", "", None, "facebook", datetime(2026, 7, 1), 1, 0, 0, 100),
            PlatformRecord(6, "history", "", None, "facebook", datetime(2026, 7, 1), 1, 0, 0, 100),
        ]
        insights = compute_summary_insights(posts, records)
        terra = [i for i in insights if i["tone"] == "terra"]
        assert len(terra) == 1
        assert "Facebook" in terra[0]["title"]

    def test_terra_needs_three_posts_on_platform(self):
        posts = [_post(None, 10) for _ in range(5)]
        records = [
            PlatformRecord(
                1, "history", "", None, "instagram", datetime(2026, 7, 1), 10, 0, 0, 100
            ),
            PlatformRecord(2, "history", "", None, "facebook", datetime(2026, 7, 1), 1, 0, 0, 100),
        ]
        insights = compute_summary_insights(posts, records)
        assert all(i["tone"] != "terra" for i in insights)

    def test_max_two_insights(self):
        posts = [_post("Cow Life", 300) for _ in range(3)] + [
            _post("Community", 10) for _ in range(3)
        ]
        records = [
            PlatformRecord(i, "history", "", None, "instagram", datetime(2026, 7, 1), 30, 0, 0, 100)
            for i in range(3)
        ] + [
            PlatformRecord(
                i + 10, "history", "", None, "facebook", datetime(2026, 7, 1), 1, 0, 0, 100
            )
            for i in range(3)
        ]
        insights = compute_summary_insights(posts, records)
        assert len(insights) <= 2


class TestPillarInsightRules:
    def _stats(self, pillar, actual, target, rate):
        return {
            "pillar": pillar,
            "actual_pct": actual,
            "target_pct": target,
            "rate": rate,
            "posts": 5,
            "engagement": 100,
        }

    def test_terra_over_indexed(self):
        stats = [
            self._stats("Events", 30.0, 15.0, 1.0),  # 15pp over, lowest rate
            self._stats("Cow Life", 40.0, 40.0, 5.0),
        ]
        insights = compute_pillar_insights(stats)
        terra = [i for i in insights if i["tone"] == "terra"]
        assert len(terra) == 1
        assert "Events" in terra[0]["title"]

    def test_sage_underused_but_works(self):
        stats = [
            self._stats("Cow Life", 10.0, 40.0, 9.0),  # under target, above-avg rate
            self._stats("Events", 50.0, 15.0, 2.0),
        ]
        insights = compute_pillar_insights(stats)
        sage = [i for i in insights if i["tone"] == "sage"]
        assert len(sage) == 1
        assert "Cow Life" in sage[0]["title"]

    def test_no_insights_without_targets(self):
        stats = [self._stats("Cow Life", 60.0, None, 5.0)]
        assert compute_pillar_insights(stats) == []


# ---------------------------------------------------------------------------
# Endpoint-level queries (frozen clock)
# ---------------------------------------------------------------------------


class TestGetSummary:
    def test_empty_db_shape(self, empty_db):
        result = unified.get_summary(empty_db, "30d", now=FROZEN_NOW)
        assert result["range"] == "30d"
        assert result["kpis"]["posts"]["value"] == 0
        assert result["kpis"]["engagement"]["value"] == 0
        assert result["kpis"]["avg_rate"]["value"] is None
        assert result["kpis"]["reach"]["value"] == 0
        assert result["kpis"]["posts"]["delta_pct"] is None
        assert result["top_post"] is None
        assert result["insights"] == []
        assert result["sources"] == {"app": 0, "history": 0}
        assert len(result["engagement_by_day"]["current"]) == 30
        assert len(result["engagement_by_day"]["previous"]) == 30

    def test_counts_current_window_posts(self, seeded_db):
        result = unified.get_summary(seeded_db, "30d", now=FROZEN_NOW)
        # In window: app post 1 (agg), app post 2, fb_1, fb_2 → 4 posts
        assert result["kpis"]["posts"]["value"] == 4
        assert result["sources"] == {"app": 2, "history": 2}

    def test_engagement_totals_and_delta(self, seeded_db):
        result = unified.get_summary(seeded_db, "30d", now=FROZEN_NOW)
        # Current: post1=118, post2=30, fb_1=50, fb_2=24 → 222
        assert result["kpis"]["engagement"]["value"] == 222
        # Previous window (Jun 14 window start - 30d): post 3 posted 2026-05-20
        # is NOT in previous window (May 15–Jun 13 → yes it IS: May 20 in range)
        assert result["kpis"]["engagement"]["delta_pct"] is not None

    def test_top_post_is_highest_engagement(self, seeded_db):
        result = unified.get_summary(seeded_db, "30d", now=FROZEN_NOW)
        top = result["top_post"]
        assert top["id"] == 1
        assert top["source"] == "app"
        assert top["engagement"] == 118
        assert top["platform"] == "instagram"
        assert top["date"] == "2026-07-01"

    def test_series_downsampled_to_max_14_buckets(self, seeded_db):
        for range_key in ("7d", "30d", "90d", "365d"):
            result = unified.get_summary(seeded_db, range_key, now=FROZEN_NOW)
            for kpi in result["kpis"].values():
                assert len(kpi["series"]) <= 14

    def test_engagement_by_day_aligned_by_index(self, seeded_db):
        result = unified.get_summary(seeded_db, "7d", now=FROZEN_NOW)
        cur = result["engagement_by_day"]["current"]
        prev = result["engagement_by_day"]["previous"]
        assert len(cur) == len(prev) == 7
        assert cur[-1]["date"] == "2026-07-14"
        assert prev[-1]["date"] == "2026-07-07"

    def test_range_windowing_excludes_outside_posts(self, seeded_db):
        result = unified.get_summary(seeded_db, "7d", now=FROZEN_NOW)
        # 7d window = Jul 8–14: app post 2 (Jul 8), fb_2 (Jul 10) → 2 posts
        assert result["kpis"]["posts"]["value"] == 2

    def test_avg_rate_none_when_no_post_has_reach(self, tmp_path):
        """Engagement without reach data → rate incomputable → honest null, not 0%."""
        db_path = tmp_path / "no_reach.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript(SCHEMA)
        conn.executescript("""
            INSERT INTO social_history (platform, external_id, post_text, hashtags,
                                        posted_at, likes, comments, shares, reach, pillar)
            VALUES ('facebook', 'fb_nr1', 'Likes but reach never imported', '[]',
                    '2026-07-05T10:00:00+0000', 40, 6, 4, 0, NULL);
            INSERT INTO social_history (platform, external_id, post_text, hashtags,
                                        posted_at, likes, comments, shares, reach, pillar)
            VALUES ('facebook', 'fb_nr2', 'Another reachless post', '[]',
                    '2026-07-10T09:00:00+0000', 20, 2, 2, 0, NULL);
        """)
        conn.commit()
        conn.close()
        result = unified.get_summary(str(db_path), "30d", now=FROZEN_NOW)
        assert result["kpis"]["engagement"]["value"] == 74
        assert result["kpis"]["avg_rate"]["value"] is None
        assert result["kpis"]["avg_rate"]["delta_pct"] is None

    def test_avg_rate_zero_when_reach_but_no_engagement(self, tmp_path):
        """Reach present with zero engagement → genuine 0.0 rate, not null."""
        db_path = tmp_path / "zero_rate.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript(SCHEMA)
        conn.executescript("""
            INSERT INTO social_history (platform, external_id, post_text, hashtags,
                                        posted_at, likes, comments, shares, reach, pillar)
            VALUES ('facebook', 'fb_z', 'Reached but ignored', '[]',
                    '2026-07-05T10:00:00+0000', 0, 0, 0, 500, NULL);
        """)
        conn.commit()
        conn.close()
        result = unified.get_summary(str(db_path), "30d", now=FROZEN_NOW)
        assert result["kpis"]["avg_rate"]["value"] == 0.0


class TestGetPosts:
    def test_empty_db(self, empty_db):
        result = unified.get_posts(empty_db, "30d", now=FROZEN_NOW)
        assert result == {"posts": [], "total": 0}

    def test_sorted_by_engagement_desc(self, seeded_db):
        result = unified.get_posts(seeded_db, "30d", now=FROZEN_NOW)
        engagements = [p["engagement"] for p in result["posts"]]
        assert engagements == sorted(engagements, reverse=True)
        assert result["total"] == 4

    def test_pagination(self, seeded_db):
        page1 = unified.get_posts(seeded_db, "30d", limit=2, offset=0, now=FROZEN_NOW)
        page2 = unified.get_posts(seeded_db, "30d", limit=2, offset=2, now=FROZEN_NOW)
        assert len(page1["posts"]) == 2
        assert len(page2["posts"]) == 2
        assert page1["total"] == page2["total"] == 4
        ids = {(p["source"], p["id"]) for p in page1["posts"] + page2["posts"]}
        assert len(ids) == 4

    def test_title_is_single_line_truncated(self, tmp_path):
        db = tmp_path / "t.db"
        conn = sqlite3.connect(str(db))
        conn.executescript(SCHEMA)
        long_text = "Line one\nLine two " + "x" * 100
        conn.execute(
            """INSERT INTO social_history (platform, external_id, post_text, posted_at, likes)
               VALUES ('facebook', 'fb_1', ?, '2026-07-10T10:00:00+0000', 5)""",
            (long_text,),
        )
        conn.commit()
        conn.close()

        result = unified.get_posts(str(db), "30d", now=FROZEN_NOW)
        title = result["posts"][0]["title"]
        assert "\n" not in title
        assert len(title) <= 81  # 80 + ellipsis

    def test_trend_up_down_flat(self, seeded_db):
        result = unified.get_posts(seeded_db, "30d", now=FROZEN_NOW)
        by_engagement = {p["engagement"]: p["trend"] for p in result["posts"]}
        # mean = 222/4 = 55.5; 118 > 1.2*55.5 → up; 24 and 30 < 0.8*55.5 → down
        assert by_engagement[118] == "up"
        assert by_engagement[30] == "down"
        assert by_engagement[50] == "flat"

    def test_platforms_list_for_multi_platform_app_post(self, seeded_db):
        result = unified.get_posts(seeded_db, "30d", now=FROZEN_NOW)
        top = result["posts"][0]
        assert sorted(top["platforms"]) == ["facebook", "instagram"]


class TestGetPillarInsights:
    def test_empty_db(self, empty_db):
        result = unified.get_pillar_insights(empty_db, "30d", now=FROZEN_NOW)
        assert result == {"pillars": [], "insights": []}

    def test_pillar_stats_with_meta(self, seeded_db):
        result = unified.get_pillar_insights(seeded_db, "30d", now=FROZEN_NOW)
        by_name = {p["pillar"]: p for p in result["pillars"]}
        assert "Cow Life" in by_name
        cow = by_name["Cow Life"]
        assert cow["color"] == "#16a34a"
        assert cow["target_pct"] == 40.0
        assert cow["posts"] == 1
        assert cow["actual_pct"] == 25.0  # 1 of 4 posts in window
        assert len(cow["weekly_series"]) == 12

    def test_null_target_stays_null(self, seeded_db):
        conn = sqlite3.connect(seeded_db)
        conn.execute("UPDATE pillars SET target_distribution = NULL")
        conn.commit()
        conn.close()
        result = unified.get_pillar_insights(seeded_db, "30d", now=FROZEN_NOW)
        assert all(p["target_pct"] is None for p in result["pillars"])

    def test_unpillared_posts_excluded_from_list(self, seeded_db):
        result = unified.get_pillar_insights(seeded_db, "30d", now=FROZEN_NOW)
        names = [p["pillar"] for p in result["pillars"]]
        assert None not in names


class TestGetPlatforms:
    def test_empty_db(self, empty_db):
        result = unified.get_platforms(empty_db, "30d", now=FROZEN_NOW)
        assert result["platforms"] == []
        assert result["heatmap"]["peak"] is None
        assert result["heatmap"]["sample_size"] == 0
        assert result["heatmap"]["hour_buckets"] == ["6a", "9a", "12p", "3p", "6p", "9p"]

    def test_platform_grouping(self, seeded_db):
        result = unified.get_platforms(seeded_db, "30d", now=FROZEN_NOW)
        by_name = {p["platform"]: p for p in result["platforms"]}
        # facebook: app row (43) + fb_1 (50) + fb_2 (24) = 3 records
        assert by_name["facebook"]["posts"] == 3
        assert by_name["facebook"]["engagement"] == 117
        # instagram: 2 app records in window
        assert by_name["instagram"]["posts"] == 2

    def test_no_invented_fields(self, seeded_db):
        result = unified.get_platforms(seeded_db, "30d", now=FROZEN_NOW)
        for p in result["platforms"]:
            assert set(p.keys()) == {"platform", "posts", "engagement", "reach", "rate"}

    def test_heatmap_sample_size_matches_window(self, seeded_db):
        result = unified.get_platforms(seeded_db, "30d", now=FROZEN_NOW)
        assert result["heatmap"]["sample_size"] == 5  # per-platform records in window


class TestGetRhythm:
    def test_empty_db(self, empty_db, tmp_path):
        cal = tmp_path / "cal.json"
        cal.write_text("[]")
        result = unified.get_rhythm(empty_db, "30d", now=FROZEN_NOW, calendar_path=cal)
        assert all(w["posted"] == 0 for w in result["weeks"])
        assert all(w["target"] is None for w in result["weeks"])
        assert result["festivals"] == []
        assert result["season"]["total_posts"] == 0
        assert result["season"]["best_slot"] is None
        assert result["season"]["avg_lead_days"] is None
        assert result["season"]["consistency"]["on_target_weeks"] is None
        assert result["season"]["consistency"]["total_weeks"] == len(result["weeks"])

    def test_weeks_cover_window_with_labels(self, seeded_db, tmp_path):
        cal = tmp_path / "cal.json"
        cal.write_text("[]")
        result = unified.get_rhythm(seeded_db, "30d", now=FROZEN_NOW, calendar_path=cal)
        # 30d window Jun 15–Jul 14 2026; Jun 15 is a Monday → 5 weeks
        assert len(result["weeks"]) == 5
        assert result["weeks"][0]["label"] == "Jun 15–21"
        assert result["weeks"][-1]["label"] == "Jul 13–19"
        # Posts: Jul 1 (wk3), Jul 7+8 (wk4), Jul 10 (wk4)
        assert result["weeks"][2]["posted"] == 1
        assert result["weeks"][3]["posted"] == 3

    def test_festival_markers(self, seeded_db, tmp_path):
        cal = tmp_path / "cal.json"
        cal.write_text(
            json.dumps(
                [
                    {"name": "Ratha Yatra", "date": "2026-07-08"},  # 2 posts within ±2d
                    {"name": "Future Fest", "date": "2026-08-01"},  # pending, within +30d
                    {"name": "Too Far", "date": "2026-09-30"},  # outside horizon
                    {"name": "Before Window", "date": "2026-05-01"},  # before window
                ]
            )
        )
        result = unified.get_rhythm(seeded_db, "30d", now=FROZEN_NOW, calendar_path=cal)
        by_name = {f["name"]: f for f in result["festivals"]}
        assert set(by_name) == {"Ratha Yatra", "Future Fest"}

        ratha = by_name["Ratha Yatra"]
        # ±2 days of Jul 8: fb_1 (Jul 7), post 2 (Jul 8), fb_2 (Jul 10)
        assert ratha["posts"] == 3
        assert ratha["pending"] is False
        assert ratha["lift_pct"] is not None

        future = by_name["Future Fest"]
        assert future["pending"] is True
        assert future["posts"] == 0
        assert future["lift_pct"] is None

    def test_avg_lead_days_app_posts_only(self, seeded_db, tmp_path):
        cal = tmp_path / "cal.json"
        cal.write_text("[]")
        result = unified.get_rhythm(seeded_db, "30d", now=FROZEN_NOW, calendar_path=cal)
        # post 1: created Jun 28 09:00 → posted Jul 1 09:00 = 3.0d
        # post 2: created Jul 7 10:00 → posted Jul 8 15:30 ≈ 1.23d
        assert result["season"]["avg_lead_days"] == pytest.approx(2.1, abs=0.05)

    def test_best_slot_from_heatmap_peak(self, seeded_db, tmp_path):
        cal = tmp_path / "cal.json"
        cal.write_text("[]")
        result = unified.get_rhythm(seeded_db, "30d", now=FROZEN_NOW, calendar_path=cal)
        slot = result["season"]["best_slot"]
        assert slot is not None
        assert slot["day"] in unified.DAY_NAMES
        assert slot["hour_bucket"] in unified.HOUR_BUCKET_LABELS


class TestGetHashtags:
    def test_empty_everything(self, empty_db):
        result = unified.get_hashtags(empty_db)
        # Table empty → lazy populate attempted from (empty) social_history
        assert result == {"hashtags": [], "source": "history"}

    def test_lazy_populate_from_social_history(self, seeded_db):
        result = unified.get_hashtags(seeded_db, platform="facebook")
        assert result["source"] == "history"
        tags = {h["hashtag"] for h in result["hashtags"]}
        assert "GitaValley" in tags

    def test_reads_performance_table_when_populated(self, seeded_db):
        conn = sqlite3.connect(seeded_db)
        conn.execute(
            """INSERT INTO hashtag_performance
               (hashtag, platform, times_used, total_engagement, avg_engagement, trend, updated_at)
               VALUES ('FarmLife', 'instagram', 4, 400, 100.0, 'rising', '2026-07-01')"""
        )
        conn.commit()
        conn.close()

        result = unified.get_hashtags(seeded_db, platform="instagram")
        assert result["source"] == "performance"
        assert result["hashtags"][0]["hashtag"] == "FarmLife"
        assert result["hashtags"][0]["trend"] == "rising"

    def test_cross_platform_fallback(self, seeded_db):
        conn = sqlite3.connect(seeded_db)
        conn.execute(
            """INSERT INTO hashtag_performance
               (hashtag, platform, times_used, total_engagement, avg_engagement, trend, updated_at)
               VALUES ('GitaValley', 'facebook', 10, 1000, 100.0, 'stable', '2026-07-01')"""
        )
        conn.commit()
        conn.close()

        # No tiktok rows → falls back to best across all platforms
        result = unified.get_hashtags(seeded_db, platform="tiktok")
        assert len(result["hashtags"]) == 1
        assert result["hashtags"][0]["hashtag"] == "GitaValley"

    def test_count_limits_results(self, seeded_db):
        conn = sqlite3.connect(seeded_db)
        for i in range(10):
            conn.execute(
                """INSERT INTO hashtag_performance
                   (hashtag, platform, times_used, total_engagement,
                    avg_engagement, trend, updated_at)
                   VALUES (?, 'facebook', 1, ?, ?, 'stable', '2026-07-01')""",
                (f"tag{i}", i * 10, float(i * 10)),
            )
        conn.commit()
        conn.close()

        result = unified.get_hashtags(seeded_db, platform="facebook", count=3)
        assert len(result["hashtags"]) == 3
        # Sorted by avg engagement desc
        assert result["hashtags"][0]["hashtag"] == "tag9"


# ---------------------------------------------------------------------------
# range="all" — no lower time bound (video-readiness W2)
# ---------------------------------------------------------------------------


def _rec(date, **kw):
    defaults = dict(
        id=1,
        source="history",
        text="",
        pillar=None,
        platform="facebook",
        likes=0,
        comments=0,
        shares=0,
        reach=0,
    )
    defaults.update(kw)
    return PlatformRecord(date=date, **defaults)


class TestResolveDays:
    def test_all_spans_to_earliest_record(self):
        recs = [_rec(datetime(2026, 7, 1, 9, 0)), _rec(datetime(2026, 6, 30, 9, 0), id=2)]
        # 2026-06-30 → 2026-07-14 inclusive = 15 days
        assert unified.resolve_days("all", recs, FROZEN_NOW) == 15

    def test_all_without_dated_records_uses_default(self):
        assert unified.resolve_days("all", [], FROZEN_NOW) == 30
        assert unified.resolve_days("all", [_rec(None)], FROZEN_NOW) == 30

    def test_fixed_ranges_pass_through(self):
        assert unified.resolve_days("7d", [], FROZEN_NOW) == 7
        assert unified.resolve_days("365d", [_rec(datetime(2022, 1, 1))], FROZEN_NOW) == 365
        assert unified.resolve_days(None, [], FROZEN_NOW) == 30


class TestAllRange:
    def test_summary_all_includes_old_history(self, seeded_db):
        result = unified.get_summary(seeded_db, "all", now=FROZEN_NOW)
        assert result["range"] == "all"
        # All 6 posts: app 1-3 + fb_1, fb_2, fb_old (2022)
        assert result["kpis"]["posts"]["value"] == 6
        assert result["sources"] == {"app": 3, "history": 3}

    def test_summary_30d_still_excludes_old_history(self, seeded_db):
        result = unified.get_summary(seeded_db, "30d", now=FROZEN_NOW)
        assert result["kpis"]["posts"]["value"] == 4
        assert result["sources"] == {"app": 2, "history": 2}

    def test_summary_all_has_no_previous_window(self, seeded_db):
        result = unified.get_summary(seeded_db, "all", now=FROZEN_NOW)
        for kpi in result["kpis"].values():
            assert kpi["delta_pct"] is None
        assert result["engagement_by_day"]["previous"] == []
        cur = result["engagement_by_day"]["current"]
        assert cur[0]["date"] == "2022-05-25"  # earliest record (fb_old)
        assert cur[-1]["date"] == "2026-07-14"

    def test_summary_all_series_still_downsampled(self, seeded_db):
        result = unified.get_summary(seeded_db, "all", now=FROZEN_NOW)
        for kpi in result["kpis"].values():
            assert len(kpi["series"]) <= 14

    def test_summary_all_empty_db_well_formed(self, empty_db):
        result = unified.get_summary(empty_db, "all", now=FROZEN_NOW)
        assert result["kpis"]["posts"]["value"] == 0
        assert len(result["engagement_by_day"]["current"]) == 30  # default span
        assert result["engagement_by_day"]["previous"] == []
        assert result["top_post"] is None

    def test_posts_all_includes_old_history(self, seeded_db):
        result = unified.get_posts(seeded_db, "all", now=FROZEN_NOW)
        assert result["total"] == 6
        engagements = {p["engagement"] for p in result["posts"]}
        assert 120 in engagements  # fb_old (100+10+10), only visible at range=all

    def test_posts_30d_excludes_old_history(self, seeded_db):
        result = unified.get_posts(seeded_db, "30d", now=FROZEN_NOW)
        assert result["total"] == 4

    def test_pillar_insights_all_counts_old_posts(self, seeded_db):
        result = unified.get_pillar_insights(seeded_db, "all", now=FROZEN_NOW)
        by_name = {p["pillar"]: p for p in result["pillars"]}
        assert by_name["Cow Life"]["posts"] == 2  # app posts 1 and 3
        assert by_name["Community"]["posts"] == 2  # app post 2 + fb_1

    def test_platforms_all_vs_30d(self, seeded_db):
        fb_all = next(
            p
            for p in unified.get_platforms(seeded_db, "all", now=FROZEN_NOW)["platforms"]
            if p["platform"] == "facebook"
        )
        fb_30 = next(
            p
            for p in unified.get_platforms(seeded_db, "30d", now=FROZEN_NOW)["platforms"]
            if p["platform"] == "facebook"
        )
        assert fb_all["posts"] == 4  # app1-fb + fb_1 + fb_2 + fb_old
        assert fb_30["posts"] == 3

    def test_rhythm_all_spans_full_history(self, seeded_db):
        result = unified.get_rhythm(seeded_db, "all", now=FROZEN_NOW)
        assert result["season"]["total_posts"] == 6
        assert len(result["weeks"]) > 52  # spans back to 2022
