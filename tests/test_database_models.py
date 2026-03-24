"""Tests for SQLAlchemy database models (Phase 1 — Task #1, Phase 3 — Task #1)."""

import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from api.models import (
    Base,
    CalendarPlan,
    ContentIteration,
    ContentRow,
    MediaAdapted,
    MediaCatalog,
    MediaPerformance,
    MediaTag,
    PublishConfig,
    Template,
    User,
)


@pytest.fixture
def engine():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create a new database session for testing."""
    with Session(engine) as session:
        yield session


class TestTableCreation:
    """Verify all 5 tables are created with correct columns."""

    def test_all_tables_exist(self, engine):
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        expected = {
            "users",
            "content_rows",
            "content_iterations",
            "templates",
            "publish_config",
            "pillars",
            # Phase 2
            "web_pages",
            "web_knowledge",
            "social_history",
            "analytics_cache",
            "hashtag_performance",
            # Phase 3
            "media_catalog",
            "media_tags",
            "media_performance",
            "media_adapted",
            "calendar_plans",
        }
        assert expected == tables

    def test_users_columns(self, engine):
        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("users")}
        assert columns == {"id", "username", "display_name", "password_hash", "created_at"}

    def test_content_rows_columns(self, engine):
        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("content_rows")}
        expected = {
            "id",
            "date",
            "pillar",
            "raw_text",
            "media_url",
            "platforms",
            "status",
            "captions",
            "postiz_ids",
            "posted_at",
            "feedback",
            "source",
            "template_id",
            "created_by",
            "media_catalog_ids",
            "audience_segment_id",
            "auto_publish_at",
            "sheet_row_number",
            "sheet_synced_at",
            "created_at",
            "updated_at",
        }
        assert expected == columns

    def test_content_iterations_columns(self, engine):
        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("content_iterations")}
        expected = {
            "id",
            "content_row_id",
            "platform",
            "old_caption",
            "new_caption",
            "refinement_instruction",
            "mode",
            "created_by",
            "created_at",
        }
        assert expected == columns

    def test_templates_columns(self, engine):
        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("templates")}
        expected = {
            "id",
            "name",
            "pillar",
            "platform_instructions",
            "raw_text_template",
            "variables",
            "schedule_pattern",
            "schedule_time",
            "default_segment_id",
            "created_by",
            "created_at",
            "updated_at",
        }
        assert expected == columns

    def test_publish_config_columns(self, engine):
        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("publish_config")}
        expected = {
            "id",
            "platform",
            "enabled",
            "delay_hours",
            "pillar_overrides",
            "updated_by",
            "updated_at",
        }
        assert expected == columns


class TestUserModel:
    def test_create_user(self, session):
        user = User(username="seth", display_name="Seth", password_hash="hashed123")
        session.add(user)
        session.commit()

        assert user.id is not None
        assert user.username == "seth"
        assert user.display_name == "Seth"
        assert user.created_at is not None

    def test_username_unique(self, session):
        session.add(User(username="seth", display_name="Seth", password_hash="h1"))
        session.commit()
        session.add(User(username="seth", display_name="Seth2", password_hash="h2"))
        with pytest.raises(Exception):  # IntegrityError
            session.commit()


class TestContentRowModel:
    def test_create_content_row(self, session):
        row = ContentRow(
            date=datetime(2026, 3, 17, tzinfo=UTC),
            pillar="spiritual_education",
            raw_text="Today's verse from Bhagavad Gita",
            platforms=json.dumps(["instagram", "facebook"]),
            status="draft",
            source="manual",
        )
        session.add(row)
        session.commit()

        assert row.id is not None
        assert row.status == "draft"
        assert row.source == "manual"
        assert row.created_at is not None

    def test_content_row_with_template_fk(self, session):
        template = Template(
            name="Weekly Verse",
            pillar="spiritual_education",
            raw_text_template="This week's verse: {{verse}}",
            variables=json.dumps([{"name": "verse", "type": "text"}]),
        )
        session.add(template)
        session.commit()

        row = ContentRow(
            date=datetime(2026, 3, 17, tzinfo=UTC),
            raw_text="BG 2.47",
            template_id=template.id,
            source="template",
        )
        session.add(row)
        session.commit()

        assert row.template_id == template.id

    def test_content_row_with_user_fk(self, session):
        user = User(username="devotee1", display_name="Devotee", password_hash="h")
        session.add(user)
        session.commit()

        row = ContentRow(
            date=datetime(2026, 3, 17, tzinfo=UTC),
            raw_text="Farm update",
            created_by=user.id,
        )
        session.add(row)
        session.commit()

        assert row.created_by == user.id


class TestContentIterationModel:
    def test_create_iteration(self, session):
        row = ContentRow(
            date=datetime(2026, 3, 17, tzinfo=UTC),
            raw_text="Original text",
        )
        session.add(row)
        session.commit()

        iteration = ContentIteration(
            content_row_id=row.id,
            platform="instagram",
            old_caption="Old caption",
            new_caption="Refined caption with hashtags",
            refinement_instruction="Add relevant hashtags",
            mode="refine",
        )
        session.add(iteration)
        session.commit()

        assert iteration.id is not None
        assert iteration.content_row_id == row.id
        assert iteration.mode == "refine"

    def test_iteration_modes(self, session):
        row = ContentRow(date=datetime(2026, 3, 17, tzinfo=UTC), raw_text="Text")
        session.add(row)
        session.commit()

        for mode in ("create", "refine", "repurpose"):
            it = ContentIteration(
                content_row_id=row.id,
                platform="facebook",
                new_caption=f"Caption for {mode}",
                mode=mode,
            )
            session.add(it)

        session.commit()
        iterations = session.query(ContentIteration).filter_by(content_row_id=row.id).all()
        assert len(iterations) == 3


class TestTemplateModel:
    def test_create_template(self, session):
        template = Template(
            name="Sunday Feast",
            pillar="events",
            platform_instructions=json.dumps(
                {
                    "instagram": "Use warm, inviting tone",
                    "facebook": "Include event details",
                }
            ),
            raw_text_template="Join us for Sunday Feast: {{menu}}",
            variables=json.dumps([{"name": "menu", "type": "text"}]),
            schedule_pattern="weekly:sunday",
        )
        session.add(template)
        session.commit()

        assert template.id is not None
        assert template.name == "Sunday Feast"
        assert template.schedule_pattern == "weekly:sunday"


class TestPublishConfigModel:
    def test_create_publish_config(self, session):
        config = PublishConfig(
            platform="instagram",
            enabled=True,
            delay_hours=4,
            pillar_overrides=json.dumps({"spiritual_education": True, "farm_ops": False}),
        )
        session.add(config)
        session.commit()

        assert config.id is not None
        assert config.enabled is True
        assert config.delay_hours == 4

    def test_platform_unique(self, session):
        session.add(PublishConfig(platform="instagram", enabled=True))
        session.commit()
        session.add(PublishConfig(platform="instagram", enabled=False))
        with pytest.raises(Exception):
            session.commit()

    def test_default_values(self, session):
        config = PublishConfig(platform="facebook")
        session.add(config)
        session.commit()

        assert config.enabled is False
        assert config.delay_hours == 2


# --- Phase 3: Media & Planning ---


class TestMediaCatalogModel:
    def test_create_media(self, session):
        media = MediaCatalog(
            filename="cow-pasture.jpg",
            local_path="media/cow-pasture.jpg",
            mime_type="image/jpeg",
            width=1920,
            height=1080,
            file_size=245000,
            tags=json.dumps(["cows", "farm", "outdoor"]),
            topic="Cow Protection",
            pillar="farm_community",
            source="upload",
        )
        session.add(media)
        session.commit()

        assert media.id is not None
        assert media.filename == "cow-pasture.jpg"
        assert media.usage_count == 0
        assert media.avg_engagement == 0.0
        assert media.created_at is not None

    def test_media_columns(self, engine):
        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("media_catalog")}
        expected = {
            "id",
            "filename",
            "original_url",
            "local_path",
            "postiz_media_id",
            "thumbnail_path",
            "mime_type",
            "width",
            "height",
            "file_size",
            "tags",
            "topic",
            "pillar",
            "source",
            "usage_count",
            "avg_engagement",
            "created_by",
            "created_at",
        }
        assert expected == columns

    def test_media_defaults(self, session):
        media = MediaCatalog(
            filename="test.png",
            local_path="media/test.png",
            mime_type="image/png",
            source="upload",
        )
        session.add(media)
        session.commit()

        assert media.usage_count == 0
        assert media.avg_engagement == 0.0
        assert media.width is None
        assert media.height is None


class TestMediaTagModel:
    def test_create_tag(self, session):
        media = MediaCatalog(
            filename="test.jpg",
            local_path="media/test.jpg",
            mime_type="image/jpeg",
            source="upload",
        )
        session.add(media)
        session.commit()

        tag = MediaTag(
            media_id=media.id,
            tag="cows",
            confidence=0.95,
            source="ai",
        )
        session.add(tag)
        session.commit()

        assert tag.id is not None
        assert tag.media_id == media.id
        assert tag.confidence == 0.95

    def test_tag_unique_constraint(self, session):
        media = MediaCatalog(
            filename="test.jpg",
            local_path="media/test.jpg",
            mime_type="image/jpeg",
            source="upload",
        )
        session.add(media)
        session.commit()

        session.add(MediaTag(media_id=media.id, tag="cows", confidence=0.9, source="ai"))
        session.commit()
        session.add(MediaTag(media_id=media.id, tag="cows", confidence=0.8, source="manual"))
        with pytest.raises(Exception):
            session.commit()

    def test_tag_columns(self, engine):
        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("media_tags")}
        assert columns == {"id", "media_id", "tag", "confidence", "source"}


class TestMediaPerformanceModel:
    def test_create_performance(self, session):
        media = MediaCatalog(
            filename="test.jpg",
            local_path="media/test.jpg",
            mime_type="image/jpeg",
            source="upload",
        )
        row = ContentRow(raw_text="Post about cows", status="published")
        session.add_all([media, row])
        session.commit()

        perf = MediaPerformance(
            media_id=media.id,
            content_row_id=row.id,
            platform="instagram",
            engagement_score=4.5,
        )
        session.add(perf)
        session.commit()

        assert perf.id is not None
        assert perf.engagement_score == 4.5
        assert perf.fetched_at is not None

    def test_performance_columns(self, engine):
        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("media_performance")}
        assert columns == {
            "id",
            "media_id",
            "content_row_id",
            "platform",
            "engagement_score",
            "fetched_at",
        }


class TestMediaAdaptedModel:
    def test_create_adapted(self, session):
        media = MediaCatalog(
            filename="test.jpg",
            local_path="media/test.jpg",
            mime_type="image/jpeg",
            source="upload",
        )
        session.add(media)
        session.commit()

        adapted = MediaAdapted(
            media_id=media.id,
            platform="instagram",
            format="post",
            adapted_path="media/adapted/test_ig_post.jpg",
            width=1080,
            height=1080,
            has_text_overlay=False,
        )
        session.add(adapted)
        session.commit()

        assert adapted.id is not None
        assert adapted.width == 1080
        assert adapted.has_text_overlay is False

    def test_adapted_columns(self, engine):
        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("media_adapted")}
        assert columns == {
            "id",
            "media_id",
            "platform",
            "format",
            "adapted_path",
            "width",
            "height",
            "has_text_overlay",
            "created_at",
        }


class TestCalendarPlanModel:
    def test_create_plan(self, session):
        plan = CalendarPlan(
            date_range_start=datetime(2026, 4, 1, tzinfo=UTC),
            date_range_end=datetime(2026, 4, 7, tzinfo=UTC),
            platforms=json.dumps(["instagram", "facebook"]),
            plan_data=json.dumps(
                [
                    {
                        "date": "2026-04-01",
                        "pillar": "spiritual_education",
                        "content_idea": "Morning verse",
                    },
                ]
            ),
            status="draft",
        )
        session.add(plan)
        session.commit()

        assert plan.id is not None
        assert plan.status == "draft"
        assert plan.created_at is not None

    def test_plan_columns(self, engine):
        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("calendar_plans")}
        assert columns == {
            "id",
            "date_range_start",
            "date_range_end",
            "platforms",
            "plan_data",
            "status",
            "created_by",
            "created_at",
        }
