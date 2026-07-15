"""Tests for the suggestion generator service (festival, pillar gap, template).

All tests use a frozen TODAY constant — never the wall clock.
"""

import json
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.models import Base, ContentRow, Pillar, SocialHistory, Suggestion, Template
from api.services.suggestion_generator import (
    generate_festival_suggestions,
    generate_pillar_gap_suggestions,
    generate_template_suggestions,
    refresh_suggestions,
)

TODAY = date(2026, 8, 1)  # ISO week 2026-W31
WEEK_KEY = "2026-W31"


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


def _write_calendar(tmp_path: Path, festivals: list[dict]) -> Path:
    path = tmp_path / "calendar.json"
    path.write_text(json.dumps(festivals))
    return path


def _festival(name: str, on: date, **overrides) -> dict:
    fest = {
        "name": name,
        "date": on.isoformat(),
        "significance": f"Significance of {name}.",
        "suggested_content_angles": [f"First angle for {name}", "Second angle"],
        "topic": "Spiritual Life",
        "content_pillar": "spiritual_education",
    }
    fest.update(overrides)
    return fest


def _content_row(pillar: str | None, days_ago: int, status: str = "posted") -> ContentRow:
    return ContentRow(
        pillar=pillar,
        raw_text="post",
        status=status,
        date=datetime.combine(TODAY - timedelta(days=days_ago), time.min),
    )


def _social_post(pillar: str | None, days_ago: int, ext_id: str) -> SocialHistory:
    return SocialHistory(
        platform="facebook",
        external_id=ext_id,
        pillar=pillar,
        posted_at=datetime.combine(TODAY - timedelta(days=days_ago), time.min),
    )


def _pillar(name: str, target: float | None, active: bool = True) -> Pillar:
    return Pillar(name=name, target_distribution=target, is_active=active)


# --- Festival generator ---


class TestFestivalGenerator:
    def test_includes_festival_within_45_days(self, tmp_path):
        path = _write_calendar(tmp_path, [_festival("Janmashtami", TODAY + timedelta(days=20))])
        result = generate_festival_suggestions(TODAY, path)
        assert len(result) == 1
        assert result[0]["type"] == "festival"
        assert result[0]["title"] == "Janmashtami"

    def test_includes_festival_today_and_on_day_45(self, tmp_path):
        path = _write_calendar(
            tmp_path,
            [
                _festival("Today Fest", TODAY),
                _festival("Edge Fest", TODAY + timedelta(days=45)),
            ],
        )
        result = generate_festival_suggestions(TODAY, path)
        assert {r["title"] for r in result} == {"Today Fest", "Edge Fest"}

    def test_excludes_festival_beyond_45_days(self, tmp_path):
        path = _write_calendar(tmp_path, [_festival("Far Fest", TODAY + timedelta(days=46))])
        assert generate_festival_suggestions(TODAY, path) == []

    def test_excludes_past_festival(self, tmp_path):
        path = _write_calendar(tmp_path, [_festival("Past Fest", TODAY - timedelta(days=1))])
        assert generate_festival_suggestions(TODAY, path) == []

    def test_note_combines_significance_and_first_angle(self, tmp_path):
        path = _write_calendar(tmp_path, [_festival("Fest", TODAY + timedelta(days=5))])
        [result] = generate_festival_suggestions(TODAY, path)
        assert "Significance of Fest." in result["note"]
        assert "First angle for Fest" in result["note"]
        assert "Second angle" not in result["note"]

    def test_note_without_angles_is_significance_only(self, tmp_path):
        fest = _festival("Fest", TODAY + timedelta(days=5), suggested_content_angles=[])
        path = _write_calendar(tmp_path, [fest])
        [result] = generate_festival_suggestions(TODAY, path)
        assert result["note"] == "Significance of Fest."

    def test_fields_and_source_key(self, tmp_path):
        on = TODAY + timedelta(days=10)
        path = _write_calendar(tmp_path, [_festival("Ratha Yatra", on)])
        [result] = generate_festival_suggestions(TODAY, path)
        assert result["pillar"] == "spiritual_education"
        assert result["suggested_date"] == on
        assert result["source_key"] == f"festival:Ratha Yatra:{on.isoformat()}"

    def test_missing_calendar_file_returns_empty(self, tmp_path):
        assert generate_festival_suggestions(TODAY, tmp_path / "missing.json") == []

    def test_malformed_entry_skipped(self, tmp_path):
        path = _write_calendar(
            tmp_path,
            [{"name": "No Date"}, _festival("Good Fest", TODAY + timedelta(days=3))],
        )
        result = generate_festival_suggestions(TODAY, path)
        assert [r["title"] for r in result] == ["Good Fest"]


# --- Pillar gap generator ---


class TestPillarGapGenerator:
    @pytest.mark.asyncio
    async def test_emits_gap_for_under_target_pillar(self, db_session):
        db_session.add_all(
            [
                _pillar("spiritual_education", 0.40),
                _pillar("farm_life", 0.25),
                *[_content_row("spiritual_education", days_ago=i) for i in range(1, 10)],
                _content_row("farm_life", days_ago=12),
            ]
        )
        await db_session.commit()

        result = await generate_pillar_gap_suggestions(db_session, TODAY)
        assert len(result) == 1
        gap = result[0]
        assert gap["type"] == "pillar_gap"
        assert gap["pillar"] == "farm_life"
        assert gap["title"] == "«farm_life» has been quiet"
        assert gap["suggested_date"] is None
        assert gap["source_key"] == f"pillar:farm_life:{WEEK_KEY}"
        # actual 10% vs target 25%, last post 12 days ago
        assert "10%" in gap["note"]
        assert "25%" in gap["note"]
        assert "12 days ago" in gap["note"]

    @pytest.mark.asyncio
    async def test_no_gap_when_within_threshold(self, db_session):
        # farm_life at 20% vs 25% target: exactly 5pp under — not > 5pp
        db_session.add_all(
            [
                _pillar("farm_life", 0.25),
                *[_content_row("spiritual_education", days_ago=i) for i in range(1, 9)],
                _content_row("farm_life", days_ago=2),
                _content_row("farm_life", days_ago=3),
            ]
        )
        await db_session.commit()

        result = await generate_pillar_gap_suggestions(db_session, TODAY)
        assert result == []

    @pytest.mark.asyncio
    async def test_inactive_pillar_skipped(self, db_session):
        db_session.add(_pillar("retired", 0.50, active=False))
        await db_session.commit()
        assert await generate_pillar_gap_suggestions(db_session, TODAY) == []

    @pytest.mark.asyncio
    async def test_pillar_without_target_skipped(self, db_session):
        db_session.add(_pillar("no_target", None))
        await db_session.commit()
        assert await generate_pillar_gap_suggestions(db_session, TODAY) == []

    @pytest.mark.asyncio
    async def test_empty_database_flags_targeted_pillars(self, db_session):
        db_session.add(_pillar("events", 0.15))
        await db_session.commit()

        result = await generate_pillar_gap_suggestions(db_session, TODAY)
        assert len(result) == 1
        assert result[0]["pillar"] == "events"
        assert "No posts recorded" in result[0]["note"]

    @pytest.mark.asyncio
    async def test_social_history_counts_toward_share(self, db_session):
        # farm_life would gap on content_rows alone; social history closes it
        db_session.add_all(
            [
                _pillar("farm_life", 0.25),
                *[_content_row("spiritual_education", days_ago=i) for i in range(1, 8)],
                *[_social_post("farm_life", days_ago=i, ext_id=f"fb-{i}") for i in range(1, 4)],
            ]
        )
        await db_session.commit()

        result = await generate_pillar_gap_suggestions(db_session, TODAY)
        assert result == []  # 3/10 = 30% >= 25% target

    @pytest.mark.asyncio
    async def test_posts_outside_window_not_counted(self, db_session):
        db_session.add_all(
            [
                _pillar("farm_life", 0.25),
                _content_row("farm_life", days_ago=31),  # outside 30d window
                _content_row("spiritual_education", days_ago=2),
            ]
        )
        await db_session.commit()

        result = await generate_pillar_gap_suggestions(db_session, TODAY)
        assert len(result) == 1
        assert result[0]["pillar"] == "farm_life"
        assert "31 days ago" in result[0]["note"]

    @pytest.mark.asyncio
    async def test_draft_rows_not_counted(self, db_session):
        db_session.add_all(
            [
                _pillar("farm_life", 0.25),
                *[_content_row("farm_life", days_ago=1, status="draft") for _ in range(5)],
            ]
        )
        await db_session.commit()

        result = await generate_pillar_gap_suggestions(db_session, TODAY)
        assert len(result) == 1  # drafts don't count as posted share
        assert "No posts recorded" in result[0]["note"]


# --- Template generator ---


class TestTemplateGenerator:
    @pytest.mark.asyncio
    async def test_emits_reminder_for_scheduled_template(self, db_session):
        db_session.add(Template(name="Weekly Wisdom", schedule_pattern="weekly:monday"))
        await db_session.commit()

        result = await generate_template_suggestions(db_session, TODAY)
        assert len(result) == 1
        reminder = result[0]
        assert reminder["type"] == "template"
        assert "Weekly Wisdom" in reminder["title"]
        assert reminder["suggested_date"] is None

    @pytest.mark.asyncio
    async def test_source_key_uses_template_id_and_iso_week(self, db_session):
        template = Template(name="Weekly Wisdom", schedule_pattern="weekly:monday")
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)

        [reminder] = await generate_template_suggestions(db_session, TODAY)
        assert reminder["source_key"] == f"template:{template.id}:{WEEK_KEY}"

    @pytest.mark.asyncio
    async def test_skips_template_without_schedule_pattern(self, db_session):
        db_session.add(Template(name="Ad-hoc", schedule_pattern=None))
        await db_session.commit()
        assert await generate_template_suggestions(db_session, TODAY) == []


# --- Refresh (upsert) ---


class TestRefreshSuggestions:
    @pytest.mark.asyncio
    async def test_refresh_inserts_candidates(self, db_session, tmp_path):
        path = _write_calendar(tmp_path, [_festival("Fest", TODAY + timedelta(days=5))])
        await refresh_suggestions(db_session, TODAY, calendar_path=path)

        rows = (await db_session.execute(select(Suggestion))).scalars().all()
        assert len(rows) == 1
        assert rows[0].status == "suggested"
        assert rows[0].source_key == f"festival:Fest:{(TODAY + timedelta(days=5)).isoformat()}"

    @pytest.mark.asyncio
    async def test_refresh_is_idempotent(self, db_session, tmp_path):
        path = _write_calendar(tmp_path, [_festival("Fest", TODAY + timedelta(days=5))])
        await refresh_suggestions(db_session, TODAY, calendar_path=path)
        await refresh_suggestions(db_session, TODAY, calendar_path=path)

        rows = (await db_session.execute(select(Suggestion))).scalars().all()
        assert len(rows) == 1

    @pytest.mark.asyncio
    async def test_refresh_updates_suggested_rows(self, db_session, tmp_path):
        on = TODAY + timedelta(days=5)
        path = _write_calendar(tmp_path, [_festival("Fest", on)])
        await refresh_suggestions(db_session, TODAY, calendar_path=path)

        path = _write_calendar(
            tmp_path, [_festival("Fest", on, significance="Updated significance.")]
        )
        await refresh_suggestions(db_session, TODAY, calendar_path=path)

        rows = (await db_session.execute(select(Suggestion))).scalars().all()
        assert len(rows) == 1
        assert "Updated significance." in rows[0].note

    @pytest.mark.asyncio
    async def test_refresh_never_resurrects_dismissed(self, db_session, tmp_path):
        path = _write_calendar(tmp_path, [_festival("Fest", TODAY + timedelta(days=5))])
        await refresh_suggestions(db_session, TODAY, calendar_path=path)

        row = (await db_session.execute(select(Suggestion))).scalar_one()
        row.status = "dismissed"
        await db_session.commit()

        await refresh_suggestions(db_session, TODAY, calendar_path=path)
        rows = (await db_session.execute(select(Suggestion))).scalars().all()
        assert len(rows) == 1
        assert rows[0].status == "dismissed"

    @pytest.mark.asyncio
    async def test_refresh_never_resurrects_drafted(self, db_session, tmp_path):
        path = _write_calendar(tmp_path, [_festival("Fest", TODAY + timedelta(days=5))])
        await refresh_suggestions(db_session, TODAY, calendar_path=path)

        row = (await db_session.execute(select(Suggestion))).scalar_one()
        row.status = "drafted"
        original_note = row.note
        await db_session.commit()

        path = _write_calendar(
            tmp_path,
            [_festival("Fest", TODAY + timedelta(days=5), significance="Changed.")],
        )
        await refresh_suggestions(db_session, TODAY, calendar_path=path)

        rows = (await db_session.execute(select(Suggestion))).scalars().all()
        assert len(rows) == 1
        assert rows[0].status == "drafted"
        assert rows[0].note == original_note

    @pytest.mark.asyncio
    async def test_refresh_deletes_stale_suggested_rows(self, db_session, tmp_path):
        """Suggested rows the generators no longer produce are expired."""
        db_session.add(
            Suggestion(
                type="pillar_gap",
                title="«farm_life» has been quiet",
                note="Old week.",
                pillar="farm_life",
                suggested_date=None,
                status="suggested",
                source_key="pillar:farm_life:2026-W30",  # previous ISO week
            )
        )
        await db_session.commit()

        path = _write_calendar(tmp_path, [_festival("Fest", TODAY + timedelta(days=5))])
        await refresh_suggestions(db_session, TODAY, calendar_path=path)

        rows = (await db_session.execute(select(Suggestion))).scalars().all()
        assert [r.source_key for r in rows] == [
            f"festival:Fest:{(TODAY + timedelta(days=5)).isoformat()}"
        ]

    @pytest.mark.asyncio
    async def test_refresh_expires_past_festival_suggestion(self, db_session, tmp_path):
        """A festival suggestion whose date has passed is removed on refresh."""
        past = TODAY - timedelta(days=2)
        path = _write_calendar(tmp_path, [_festival("Past Fest", past)])
        db_session.add(
            Suggestion(
                type="festival",
                title="Past Fest",
                note="n",
                suggested_date=past,
                status="suggested",
                source_key=f"festival:Past Fest:{past.isoformat()}",
            )
        )
        await db_session.commit()

        await refresh_suggestions(db_session, TODAY, calendar_path=path)
        rows = (await db_session.execute(select(Suggestion))).scalars().all()
        assert rows == []

    @pytest.mark.asyncio
    async def test_refresh_keeps_stale_dismissed_and_drafted(self, db_session, tmp_path):
        """Dismissed/drafted rows are dedup history — never expired."""
        db_session.add_all(
            [
                Suggestion(
                    type="pillar_gap",
                    title="A",
                    note="n",
                    status="dismissed",
                    source_key="pillar:farm_life:2026-W01",
                ),
                Suggestion(
                    type="template",
                    title="B",
                    note="n",
                    status="drafted",
                    source_key="template:9:2026-W01",
                ),
            ]
        )
        await db_session.commit()

        path = _write_calendar(tmp_path, [_festival("Fest", TODAY + timedelta(days=5))])
        await refresh_suggestions(db_session, TODAY, calendar_path=path)

        rows = (await db_session.execute(select(Suggestion))).scalars().all()
        statuses = {r.source_key: r.status for r in rows}
        assert statuses["pillar:farm_life:2026-W01"] == "dismissed"
        assert statuses["template:9:2026-W01"] == "drafted"
        assert len(rows) == 3  # 2 kept + 1 fresh festival

    @pytest.mark.asyncio
    async def test_refresh_resolves_pillar_slug_to_table_name(self, db_session, tmp_path):
        """Calendar slugs resolve to canonical pillars-table names."""
        db_session.add(_pillar("Spiritual Education", 0.40))
        await db_session.commit()

        # _festival() sets content_pillar="spiritual_education" (slug form)
        path = _write_calendar(tmp_path, [_festival("Fest", TODAY + timedelta(days=5))])
        await refresh_suggestions(db_session, TODAY, calendar_path=path)

        row = (
            await db_session.execute(select(Suggestion).where(Suggestion.type == "festival"))
        ).scalar_one()
        assert row.pillar == "Spiritual Education"

    @pytest.mark.asyncio
    async def test_refresh_keeps_unmatched_pillar_raw(self, db_session, tmp_path):
        """Pillar values with no pillars-table match fall back to the raw value."""
        path = _write_calendar(
            tmp_path,
            [_festival("Fest", TODAY + timedelta(days=5), content_pillar="mystery_pillar")],
        )
        await refresh_suggestions(db_session, TODAY, calendar_path=path)

        row = (await db_session.execute(select(Suggestion))).scalar_one()
        assert row.pillar == "mystery_pillar"

    @pytest.mark.asyncio
    async def test_refresh_survives_concurrent_duplicate_insert(
        self, db_session, tmp_path, monkeypatch
    ):
        """A row committed between SELECT and INSERT must not raise a UNIQUE error."""
        from sqlalchemy import text

        import api.services.suggestion_generator as generator_module

        on = TODAY + timedelta(days=5)
        path = _write_calendar(tmp_path, [_festival("Fest", on)])
        key = f"festival:Fest:{on.isoformat()}"

        # Simulate the race: the row already exists, but the upsert's
        # SELECT misses it (as if a concurrent refresh committed the same
        # source_key after our SELECT ran).
        db_session.add(
            Suggestion(
                type="festival",
                title="Fest",
                note="n",
                suggested_date=on,
                status="suggested",
                source_key=key,
            )
        )
        await db_session.commit()

        def blind_select(*args, **kwargs):
            return select(*args, **kwargs).where(text("1 = 0"))

        monkeypatch.setattr(generator_module, "select", blind_select)

        await refresh_suggestions(db_session, TODAY, calendar_path=path)  # must not raise

        rows = (await db_session.execute(select(Suggestion))).scalars().all()
        assert len(rows) == 1
        assert rows[0].source_key == key

    @pytest.mark.asyncio
    async def test_refresh_combines_all_generators(self, db_session, tmp_path):
        path = _write_calendar(tmp_path, [_festival("Fest", TODAY + timedelta(days=5))])
        db_session.add_all(
            [
                _pillar("events", 0.15),
                Template(name="Weekly Wisdom", schedule_pattern="weekly:monday"),
            ]
        )
        await db_session.commit()

        await refresh_suggestions(db_session, TODAY, calendar_path=path)
        rows = (await db_session.execute(select(Suggestion))).scalars().all()
        assert {r.type for r in rows} == {"festival", "pillar_gap", "template"}
