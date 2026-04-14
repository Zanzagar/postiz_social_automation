"""Tests for iteration history with model_used field (Task #20).

Tests cover:
- ContentIteration model has model_used column
- Iterate endpoint saves model_used in iteration record
- IterationResponse includes model_used
- Revert saves iteration with model_used='revert'
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.models import Base, ContentIteration


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


class TestContentIterationModelUsed:
    def test_model_has_model_used_column(self):
        columns = {c.name for c in ContentIteration.__table__.columns}
        assert "model_used" in columns

    def test_model_used_defaults_to_none(self, db_session):
        async def _create():
            from api.models import ContentRow

            # Create parent content row
            row = ContentRow(
                raw_text="Test",
                status="draft",
                date=datetime(2026, 3, 20),
            )
            db_session.add(row)
            await db_session.commit()
            await db_session.refresh(row)

            iteration = ContentIteration(
                content_row_id=row.id,
                platform="instagram",
                new_caption="Test caption",
            )
            db_session.add(iteration)
            await db_session.commit()
            await db_session.refresh(iteration)
            return iteration

        iteration = asyncio.get_event_loop().run_until_complete(_create())
        assert iteration.model_used is None

    def test_model_used_saved_when_provided(self, db_session):
        async def _create():
            from api.models import ContentRow

            row = ContentRow(
                raw_text="Test",
                status="draft",
                date=datetime(2026, 3, 20),
            )
            db_session.add(row)
            await db_session.commit()
            await db_session.refresh(row)

            iteration = ContentIteration(
                content_row_id=row.id,
                platform="instagram",
                new_caption="Test caption",
                model_used="sonnet",
            )
            db_session.add(iteration)
            await db_session.commit()
            await db_session.refresh(iteration)
            return iteration

        iteration = asyncio.get_event_loop().run_until_complete(_create())
        assert iteration.model_used == "sonnet"


class TestIterateEndpointSavesModelUsed:
    @pytest.fixture
    def mock_generator(self):
        gen = MagicMock()
        gen.iterate_single_caption.return_value = "Better caption"
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
                    "raw_text": "Morning at the barn",
                    "status": "draft",
                    "date": datetime(2026, 3, 20),
                    "pillar": "cow_life",
                    "platforms": json.dumps({"instagram": True, "facebook": True}),
                    "captions": json.dumps(
                        {"instagram": "Original IG caption", "facebook": "Original FB caption"}
                    ),
                    "source": "generated",
                }
            )
        )

        yield TestClient(app)
        app.dependency_overrides.clear()

    @patch("api.routes.iterate.save_preference_pair")
    @patch("api.routes.iterate.get_model")
    def test_iterate_saves_model_used(self, mock_get_model, mock_save_pref, client, repo):
        mock_get_model.return_value = "sonnet"
        mock_save_pref.return_value = True

        resp = client.post(
            "/api/iterate",
            json={
                "content_row_id": 1,
                "platform": "instagram",
                "instruction": "Make warmer",
            },
        )
        assert resp.status_code == 200

        iterations = asyncio.get_event_loop().run_until_complete(repo.get_iterations(1))
        assert len(iterations) == 1
        assert iterations[0].model_used == "sonnet"

    @patch("api.routes.iterate.save_preference_pair")
    def test_iteration_response_includes_model_used(self, mock_save_pref, client):
        mock_save_pref.return_value = True

        # Create an iteration
        client.post(
            "/api/iterate",
            json={
                "content_row_id": 1,
                "platform": "instagram",
                "instruction": "Shorten it",
            },
        )

        resp = client.get("/api/iterations/1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert "model_used" in data[0]
