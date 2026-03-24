"""Tests for few-shot example storage and retrieval."""

import sqlite3

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.models import Base
from content_engine.few_shot import get_few_shot_examples

# --- Unit tests for retrieval ---


@pytest.fixture
def examples_db(tmp_path):
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    conn.executescript("""
        CREATE TABLE few_shot_examples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            pillar TEXT,
            raw_text TEXT,
            caption TEXT NOT NULL,
            engagement_score REAL DEFAULT 0.0,
            is_active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        INSERT INTO few_shot_examples
            (platform, pillar, raw_text, caption, engagement_score) VALUES
            ('instagram', 'Cow Life', 'cow update',
             'Meet Nandini! She loves morning walks.', 80.0),
            ('instagram', 'Cow Life', 'new calf',
             'Our newest family member arrived at dawn.', 65.0),
            ('instagram', 'Farm Ops', 'cheese day',
             'Fresh paneer made with love today.', 45.0),
            ('facebook', 'Community', 'event',
             'You are invited to our Chariot Festival!', 50.0),
            ('instagram', 'Cow Life', 'old cow',
             'Inactive example', 30.0);

        UPDATE few_shot_examples SET is_active = 0 WHERE id = 5;
    """)
    conn.commit()
    conn.close()
    return str(db)


class TestGetFewShotExamples:
    def test_returns_by_platform(self, examples_db):
        results = get_few_shot_examples(examples_db, platform="instagram")
        assert len(results) >= 1
        for r in results:
            assert r["platform"] == "instagram"

    def test_filters_by_pillar(self, examples_db):
        results = get_few_shot_examples(examples_db, platform="instagram", pillar="Cow Life")
        for r in results:
            assert r["pillar"] == "Cow Life"

    def test_ordered_by_engagement(self, examples_db):
        results = get_few_shot_examples(examples_db, platform="instagram", pillar="Cow Life")
        scores = [r["engagement_score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_respects_limit(self, examples_db):
        results = get_few_shot_examples(examples_db, platform="instagram", limit=2)
        assert len(results) <= 2

    def test_excludes_inactive(self, examples_db):
        results = get_few_shot_examples(
            examples_db, platform="instagram", pillar="Cow Life", limit=10
        )
        captions = [r["caption"] for r in results]
        assert "Inactive example" not in captions

    def test_returns_caption_and_raw_text(self, examples_db):
        results = get_few_shot_examples(examples_db, platform="instagram")
        for r in results:
            assert "caption" in r
            assert "raw_text" in r

    def test_empty_for_unknown_platform(self, examples_db):
        results = get_few_shot_examples(examples_db, platform="tiktok")
        assert results == []

    def test_graceful_when_no_table(self, tmp_path):
        db = tmp_path / "empty.db"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE dummy (id INTEGER)")
        conn.commit()
        conn.close()
        results = get_few_shot_examples(str(db), platform="instagram")
        assert results == []


# --- API tests ---


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    from api.dependencies import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def _env_vars(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-key-min-32-chars!!")
    monkeypatch.setenv("API_PASSWORD", "testpass")
    monkeypatch.setenv("POSTIZ_API_KEY", "test-key")
    monkeypatch.setenv("SPREADSHEET_ID", "test-sheet")
    monkeypatch.setenv("GOOGLE_SHEETS_CREDENTIALS", "/tmp/creds.json")
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
def client(_env_vars, db_session):
    from api.auth import get_current_user
    from api.dependencies import get_db
    from api.main import app

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: {"sub": "test"}
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestFewShotAPI:
    def test_get_empty(self, client):
        resp = client.get("/api/settings/few-shot")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_post_and_get(self, client):
        resp = client.post(
            "/api/settings/few-shot",
            json={
                "platform": "instagram",
                "pillar": "Cow Life",
                "caption": "Meet Nandini!",
                "raw_text": "cow update",
                "engagement_score": 80.0,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["caption"] == "Meet Nandini!"
        assert data["id"] > 0

        # GET should return it
        resp2 = client.get("/api/settings/few-shot")
        assert len(resp2.json()) == 1

    def test_delete(self, client):
        # Create then delete
        resp = client.post(
            "/api/settings/few-shot",
            json={
                "platform": "instagram",
                "caption": "Delete me",
            },
        )
        ex_id = resp.json()["id"]

        resp2 = client.delete(f"/api/settings/few-shot/{ex_id}")
        assert resp2.status_code == 200

        # Should be gone
        resp3 = client.get("/api/settings/few-shot")
        assert len(resp3.json()) == 0
