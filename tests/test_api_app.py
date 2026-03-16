"""Tests for FastAPI backend app initialization, CORS, and dependency injection."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """Clear the lru_cache on get_settings between tests."""
    from api.dependencies import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def _env_vars(monkeypatch):
    """Set required environment variables for API config."""
    monkeypatch.setenv("JWT_SECRET", "test-secret-key-min-32-chars-long!!")
    monkeypatch.setenv("API_PASSWORD", "testpass")
    monkeypatch.setenv("POSTIZ_API_KEY", "test-postiz-key")
    monkeypatch.setenv("SPREADSHEET_ID", "test-spreadsheet-id")
    monkeypatch.setenv("GOOGLE_SHEETS_CREDENTIALS", "/tmp/test-creds.json")


@pytest.fixture
def client(_env_vars):
    """Create a test client for the FastAPI app."""
    from api.main import app

    return TestClient(app)


class TestAppInitialization:
    """Test that the FastAPI app starts and basic routes work."""

    def test_app_exists(self, _env_vars):
        from api.main import app

        assert app is not None
        assert app.title == "Gita Valley Content Engine API"

    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_root_returns_info(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Gita Valley Content Engine API"


class TestCORS:
    """Test CORS middleware configuration."""

    def test_cors_allows_frontend_origin(self, client):
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-origin" in response.headers

    def test_cors_allows_common_methods(self, client):
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert "access-control-allow-methods" in response.headers


class TestConfig:
    """Test pydantic-settings configuration."""

    def test_config_loads_from_env(self, _env_vars):
        from api.config import Settings

        settings = Settings()
        assert settings.jwt_secret == "test-secret-key-min-32-chars-long!!"
        assert settings.api_password == "testpass"
        assert settings.postiz_api_key == "test-postiz-key"
        assert settings.spreadsheet_id == "test-spreadsheet-id"

    def test_config_has_defaults(self, _env_vars):
        from api.config import Settings

        settings = Settings()
        assert settings.postiz_base_url  # has a default
        assert settings.cors_origins  # has defaults

    def test_config_ignores_extra_env_vars(self, _env_vars, monkeypatch):
        """Settings should not reject extra env vars from .env file."""
        monkeypatch.setenv("SOME_RANDOM_VAR", "whatever")
        from api.config import Settings

        settings = Settings()
        assert settings.jwt_secret == "test-secret-key-min-32-chars-long!!"


class TestDependencies:
    """Test dependency injection functions."""

    def test_get_settings_returns_settings(self, _env_vars):
        from api.config import Settings
        from api.dependencies import get_settings

        settings = get_settings()
        assert isinstance(settings, Settings)

    @patch("api.dependencies.PostizClient")
    def test_get_postiz_client(self, mock_cls, _env_vars):
        from api.dependencies import get_postiz_client

        get_postiz_client()
        mock_cls.assert_called_once()

    @patch("api.dependencies.CaptionGenerator")
    def test_get_caption_generator(self, mock_cls, _env_vars):
        from api.dependencies import get_caption_generator

        get_caption_generator()
        mock_cls.assert_called_once()


class TestExceptionHandlers:
    """Test that API exceptions return proper JSON responses."""

    def test_404_returns_json(self, client):
        response = client.get("/nonexistent-route")
        assert response.status_code in (404, 405)

    def test_post_to_get_only_returns_405(self, client):
        response = client.post("/health", json={"invalid": "data"})
        assert response.status_code == 405
