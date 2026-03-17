"""Tests for SQLAlchemy database models (Phase 1 — Task #1)."""

import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from api.models import Base, ContentIteration, ContentRow, PublishConfig, Template, User


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
        expected = {"users", "content_rows", "content_iterations", "templates", "publish_config"}
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
