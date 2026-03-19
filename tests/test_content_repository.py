"""Tests for ContentRepository async CRUD operations (Phase 1 — Task #2)."""

import json
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.models import Base
from api.repositories.content import ContentRepository


@pytest_asyncio.fixture
async def async_session():
    """Create an async in-memory SQLite session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def repo(async_session):
    """Create a ContentRepository for testing."""
    return ContentRepository(async_session)


# --- ContentRow CRUD ---


class TestContentRowCRUD:
    @pytest.mark.asyncio
    async def test_create_content_row(self, repo, async_session):
        row = await repo.create_content_row(
            {
                "date": datetime(2026, 3, 17, tzinfo=UTC),
                "pillar": "spiritual_education",
                "raw_text": "BG 2.47 — Focus on action, not results",
                "platforms": json.dumps(["instagram", "facebook"]),
                "status": "draft",
                "source": "manual",
            }
        )
        assert row.id is not None
        assert row.status == "draft"

    @pytest.mark.asyncio
    async def test_get_content_row(self, repo, async_session):
        row = await repo.create_content_row(
            {
                "date": datetime(2026, 3, 17, tzinfo=UTC),
                "raw_text": "Test content",
            }
        )
        fetched = await repo.get_content_row(row.id)
        assert fetched is not None
        assert fetched.raw_text == "Test content"

    @pytest.mark.asyncio
    async def test_get_content_row_not_found(self, repo):
        result = await repo.get_content_row(999)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_content_rows(self, repo, async_session):
        await repo.create_content_row({"raw_text": "Row 1"})
        await repo.create_content_row({"raw_text": "Row 2"})
        rows = await repo.get_all_content_rows()
        assert len(rows) == 2

    @pytest.mark.asyncio
    async def test_get_rows_by_status(self, repo, async_session):
        await repo.create_content_row({"raw_text": "Draft", "status": "draft"})
        await repo.create_content_row({"raw_text": "Ready", "status": "ready"})
        await repo.create_content_row({"raw_text": "Draft2", "status": "draft"})

        drafts = await repo.get_rows_by_status("draft")
        assert len(drafts) == 2

    @pytest.mark.asyncio
    async def test_update_captions(self, repo, async_session):
        row = await repo.create_content_row({"raw_text": "Test"})
        captions = json.dumps({"instagram": "Insta caption", "facebook": "FB caption"})
        await repo.update_captions(row.id, captions)

        updated = await repo.get_content_row(row.id)
        parsed = json.loads(updated.captions)
        assert parsed["instagram"] == "Insta caption"

    @pytest.mark.asyncio
    async def test_update_status(self, repo, async_session):
        row = await repo.create_content_row({"raw_text": "Test", "status": "draft"})
        await repo.update_status(row.id, "ready")

        updated = await repo.get_content_row(row.id)
        assert updated.status == "ready"

    @pytest.mark.asyncio
    async def test_update_postiz_ids(self, repo, async_session):
        row = await repo.create_content_row({"raw_text": "Test"})
        postiz_ids = json.dumps({"instagram": "pid-123"})
        await repo.update_postiz_ids(
            row.id, postiz_ids, posted_at=datetime(2026, 3, 17, tzinfo=UTC)
        )

        updated = await repo.get_content_row(row.id)
        assert json.loads(updated.postiz_ids)["instagram"] == "pid-123"
        assert updated.posted_at is not None

    @pytest.mark.asyncio
    async def test_delete_content_row(self, repo, async_session):
        row = await repo.create_content_row({"raw_text": "To delete"})
        result = await repo.delete_content_row(row.id)
        assert result is True
        assert await repo.get_content_row(row.id) is None

    @pytest.mark.asyncio
    async def test_get_rows_by_date_range(self, repo, async_session):
        await repo.create_content_row(
            {
                "raw_text": "March 15",
                "date": datetime(2026, 3, 15, tzinfo=UTC),
            }
        )
        await repo.create_content_row(
            {
                "raw_text": "March 20",
                "date": datetime(2026, 3, 20, tzinfo=UTC),
            }
        )
        await repo.create_content_row(
            {
                "raw_text": "March 25",
                "date": datetime(2026, 3, 25, tzinfo=UTC),
            }
        )

        rows = await repo.get_rows_by_date_range(
            datetime(2026, 3, 14, tzinfo=UTC),
            datetime(2026, 3, 21, tzinfo=UTC),
        )
        assert len(rows) == 2


# --- ContentIteration CRUD ---


class TestIterationCRUD:
    @pytest.mark.asyncio
    async def test_add_iteration(self, repo, async_session):
        row = await repo.create_content_row({"raw_text": "Original"})
        iteration = await repo.add_iteration(
            {
                "content_row_id": row.id,
                "platform": "instagram",
                "old_caption": "Old",
                "new_caption": "Refined with hashtags",
                "refinement_instruction": "Add hashtags",
                "mode": "refine",
            }
        )
        assert iteration.id is not None
        assert iteration.mode == "refine"

    @pytest.mark.asyncio
    async def test_get_iterations(self, repo, async_session):
        row = await repo.create_content_row({"raw_text": "Original"})
        await repo.add_iteration(
            {
                "content_row_id": row.id,
                "platform": "instagram",
                "new_caption": "V1",
                "mode": "create",
            }
        )
        await repo.add_iteration(
            {
                "content_row_id": row.id,
                "platform": "instagram",
                "new_caption": "V2",
                "mode": "refine",
            }
        )

        iterations = await repo.get_iterations(row.id)
        assert len(iterations) == 2


# --- Template CRUD ---


class TestTemplateCRUD:
    @pytest.mark.asyncio
    async def test_create_template(self, repo, async_session):
        template = await repo.create_template(
            {
                "name": "Test Template",
                "pillar": "events",
                "raw_text_template": "Event: {{name}}",
                "variables": json.dumps([{"name": "name", "type": "text"}]),
            }
        )
        assert template.id is not None

    @pytest.mark.asyncio
    async def test_get_templates(self, repo, async_session):
        await repo.create_template({"name": "T1", "raw_text_template": "{{x}}"})
        await repo.create_template({"name": "T2", "raw_text_template": "{{y}}"})
        templates = await repo.get_templates()
        assert len(templates) == 2

    @pytest.mark.asyncio
    async def test_get_template(self, repo, async_session):
        t = await repo.create_template({"name": "Specific", "raw_text_template": "{{z}}"})
        fetched = await repo.get_template(t.id)
        assert fetched.name == "Specific"

    @pytest.mark.asyncio
    async def test_update_template(self, repo, async_session):
        t = await repo.create_template({"name": "Old Name", "raw_text_template": "{{x}}"})
        updated = await repo.update_template(t.id, {"name": "New Name"})
        assert updated.name == "New Name"

    @pytest.mark.asyncio
    async def test_delete_template(self, repo, async_session):
        t = await repo.create_template({"name": "To Delete", "raw_text_template": "{{x}}"})
        result = await repo.delete_template(t.id)
        assert result is True
        assert await repo.get_template(t.id) is None


# --- PublishConfig CRUD ---


class TestPublishConfigCRUD:
    @pytest.mark.asyncio
    async def test_get_publish_configs(self, repo, async_session):
        await repo.upsert_publish_config("instagram", {"enabled": True, "delay_hours": 4})
        await repo.upsert_publish_config("facebook", {"enabled": False})
        configs = await repo.get_publish_configs()
        assert len(configs) == 2

    @pytest.mark.asyncio
    async def test_upsert_publish_config_create(self, repo, async_session):
        config = await repo.upsert_publish_config(
            "instagram",
            {
                "enabled": True,
                "delay_hours": 3,
            },
        )
        assert config.platform == "instagram"
        assert config.enabled is True

    @pytest.mark.asyncio
    async def test_upsert_publish_config_update(self, repo, async_session):
        await repo.upsert_publish_config("instagram", {"enabled": True, "delay_hours": 2})
        updated = await repo.upsert_publish_config(
            "instagram", {"enabled": False, "delay_hours": 5}
        )
        assert updated.enabled is False
        assert updated.delay_hours == 5

        configs = await repo.get_publish_configs()
        assert len(configs) == 1  # Not duplicated
