"""Tests for brand settings table, API, and prompt context."""

import sqlite3

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.models import Base
from content_engine.prompt_builder import get_brand_context

# --- Unit tests for get_brand_context ---


class TestGetBrandContext:
    def test_returns_formatted_string_with_defaults(self, tmp_path):
        db = tmp_path / "test.db"
        conn = sqlite3.connect(str(db))
        conn.executescript("""
            CREATE TABLE brand_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO brand_settings (key, value) VALUES
                ('brand_name', 'Gita Valley'),
                ('tagline', 'Cultivating Soil and Soul'),
                ('website', 'gitavalley.org'),
                ('key_claim', 'Only USDA Certified Slaughter-Free Dairy'),
                ('products', 'Ahimsa dairy — paneer, cheddar');
        """)
        conn.commit()
        conn.close()

        ctx = get_brand_context(str(db))
        assert "Gita Valley" in ctx
        assert "Cultivating Soil and Soul" in ctx
        assert "gitavalley.org" in ctx
        assert "Slaughter-Free" in ctx
        assert "paneer" in ctx

    def test_returns_empty_when_no_table(self, tmp_path):
        db = tmp_path / "empty.db"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE dummy (id INTEGER)")
        conn.commit()
        conn.close()

        ctx = get_brand_context(str(db))
        assert ctx == ""

    def test_returns_empty_when_no_rows(self, tmp_path):
        db = tmp_path / "test.db"
        conn = sqlite3.connect(str(db))
        conn.execute("""
            CREATE TABLE brand_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

        ctx = get_brand_context(str(db))
        assert ctx == ""

    def test_custom_values(self, tmp_path):
        db = tmp_path / "test.db"
        conn = sqlite3.connect(str(db))
        conn.executescript("""
            CREATE TABLE brand_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO brand_settings (key, value) VALUES
                ('brand_name', 'Krishna Farm'),
                ('tagline', 'Simple Living High Thinking');
        """)
        conn.commit()
        conn.close()

        ctx = get_brand_context(str(db))
        assert "Krishna Farm" in ctx
        assert "Simple Living" in ctx
        assert "Gita Valley" not in ctx


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


class TestBrandSettingsAPI:
    def test_get_empty(self, client):
        resp = client.get("/api/settings/brand")
        assert resp.status_code == 200
        assert resp.json() == {}

    def test_put_and_get(self, client):
        resp = client.put(
            "/api/settings/brand",
            json={"brand_name": "Gita Valley", "tagline": "Cultivating"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["brand_name"] == "Gita Valley"
        assert data["tagline"] == "Cultivating"

        # GET should return the same
        resp2 = client.get("/api/settings/brand")
        assert resp2.json() == data

    def test_put_partial_update(self, client):
        # Set initial values
        client.put(
            "/api/settings/brand",
            json={"brand_name": "Farm A", "website": "farm-a.org"},
        )
        # Update only brand_name
        resp = client.put(
            "/api/settings/brand",
            json={"brand_name": "Farm B"},
        )
        data = resp.json()
        assert data["brand_name"] == "Farm B"
        assert data["website"] == "farm-a.org"  # Unchanged

    def test_put_creates_new_keys(self, client):
        resp = client.put(
            "/api/settings/brand",
            json={"key_claim": "Best farm", "products": "Cheese"},
        )
        data = resp.json()
        assert data["key_claim"] == "Best farm"
        assert data["products"] == "Cheese"
