"""Tests for preference pair SQLAlchemy model and iterate endpoint wiring.

Tests cover:
- PreferencePair model exists and has correct columns
- Iterate endpoint calls save_preference_pair after successful iteration
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.models import Base, PreferencePair


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    from api.dependencies import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def _env_vars(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-key-min-32-chars-long!!")
    monkeypatch.setenv("API_PASSWORD", "testpass")
    monkeypatch.setenv("POSTIZ_API_KEY", "test-postiz-key")
    monkeypatch.setenv("SPREADSHEET_ID", "test-spreadsheet-id")
    monkeypatch.setenv("GOOGLE_SHEETS_CREDENTIALS", "/tmp/test-creds.json")
    monkeypatch.setenv("DATABASE_PATH", ":memory:")


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def repo(db_session):
    from api.repositories.content import ContentRepository

    return ContentRepository(db_session)


class TestPreferencePairModel:
    def test_model_has_expected_columns(self):
        columns = {c.name for c in PreferencePair.__table__.columns}
        expected = {"id", "platform", "original_text", "edited_text", "instruction", "created_at"}
        assert expected == columns

    def test_table_name(self):
        assert PreferencePair.__tablename__ == "preference_pairs"

    def test_can_create_record(self, db_session):
        async def _create():
            pair = PreferencePair(
                platform="instagram",
                original_text="Original caption",
                edited_text="Edited caption",
                instruction="Make it shorter",
            )
            db_session.add(pair)
            await db_session.commit()
            await db_session.refresh(pair)
            return pair

        pair = asyncio.get_event_loop().run_until_complete(_create())
        assert pair.id is not None
        assert pair.platform == "instagram"
        assert pair.original_text == "Original caption"
        assert pair.edited_text == "Edited caption"
        assert pair.instruction == "Make it shorter"
        assert pair.created_at is not None


class TestIterateEndpointPreferencePairWiring:
    @pytest.fixture
    def mock_generator(self):
        gen = MagicMock()
        gen.iterate_single_caption.return_value = "New improved caption"
        return gen

    @pytest.fixture
    def client(self, _env_vars, db_session, repo, mock_generator):
        from api.auth import get_current_user
        from api.dependencies import get_caption_generator, get_content_repo, get_db
        from api.main import app

        async def override_db():
            yield db_session

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_content_repo] = lambda: repo
        app.dependency_overrides[get_current_user] = lambda: {"sub": "testuser"}
        app.dependency_overrides[get_caption_generator] = lambda: mock_generator

        # Seed a content row
        asyncio.get_event_loop().run_until_complete(
            repo.create_content_row(
                {
                    "raw_text": "Morning at the barn with Lakshmi",
                    "status": "draft",
                    "date": datetime(2026, 3, 20),
                    "pillar": "cow_life",
                    "platforms": json.dumps({"instagram": True}),
                    "captions": json.dumps({"instagram": "Original IG caption"}),
                    "source": "generated",
                }
            )
        )

        yield TestClient(app)
        app.dependency_overrides.clear()

    @patch("api.routes.iterate.save_preference_pair")
    def test_iterate_calls_save_preference_pair(self, mock_save, client):
        mock_save.return_value = True

        resp = client.post(
            "/api/iterate",
            json={
                "content_row_id": 1,
                "platform": "instagram",
                "instruction": "Make it warmer",
            },
        )
        assert resp.status_code == 200

        mock_save.assert_called_once_with(
            db_path=":memory:",
            original="Original IG caption",
            edited="New improved caption",
            platform="instagram",
            instruction="Make it warmer",
        )

    @patch("api.routes.iterate.save_preference_pair")
    def test_iterate_with_none_original_passes_empty_string(self, mock_save, client, repo):
        mock_save.return_value = True

        # Remove the instagram caption
        asyncio.get_event_loop().run_until_complete(
            repo.update_captions(1, json.dumps({"facebook": "FB caption"}))
        )

        resp = client.post(
            "/api/iterate",
            json={
                "content_row_id": 1,
                "platform": "instagram",
                "instruction": "Create new",
            },
        )
        assert resp.status_code == 200

        mock_save.assert_called_once_with(
            db_path=":memory:",
            original="",
            edited="New improved caption",
            platform="instagram",
            instruction="Create new",
        )

    @patch("api.routes.iterate.save_preference_pair")
    def test_iterate_succeeds_even_if_preference_save_fails(self, mock_save, client):
        mock_save.side_effect = RuntimeError("DB error")

        resp = client.post(
            "/api/iterate",
            json={
                "content_row_id": 1,
                "platform": "instagram",
                "instruction": "Make it shorter",
            },
        )
        # Should still return 200 — preference pair saving is fire-and-forget
        assert resp.status_code == 200
        assert resp.json()["caption"] == "New improved caption"
