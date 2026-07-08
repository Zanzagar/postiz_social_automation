"""Tests for JWT authentication endpoints and middleware."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _clear_caches():
    """Clear caches and rate limit state between tests."""
    from api.dependencies import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def _env_vars(monkeypatch):
    """Set required environment variables."""
    monkeypatch.setenv("JWT_SECRET", "test-secret-key-min-32-chars-long!!")
    monkeypatch.setenv("API_PASSWORD", "correctpassword")
    monkeypatch.setenv("POSTIZ_API_KEY", "test-postiz-key")
    monkeypatch.setenv("SPREADSHEET_ID", "test-spreadsheet-id")
    monkeypatch.setenv("GOOGLE_SHEETS_CREDENTIALS", "/tmp/test-creds.json")


@pytest.fixture
def client(_env_vars):
    """Create a test client."""
    from api.auth import _failed_attempts

    _failed_attempts.clear()

    from api.main import app

    return TestClient(app)


class TestLogin:
    """Test POST /api/auth/login."""

    def test_login_correct_password(self, client):
        response = client.post("/api/auth/login", json={"password": "correctpassword"})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client):
        response = client.post("/api/auth/login", json={"password": "wrong"})
        assert response.status_code == 401
        detail = response.json()["detail"]
        assert detail["message"] == "invalid_password"
        assert detail["attempts_remaining"] == 4

    def test_attempts_remaining_decrements_then_locks(self, client):
        """Each failed login reports remaining tries; 6th request is locked out."""
        for expected in (4, 3, 2, 1, 0):
            response = client.post("/api/auth/login", json={"password": "wrong"})
            assert response.status_code == 401
            assert response.json()["detail"]["attempts_remaining"] == expected

        response = client.post("/api/auth/login", json={"password": "wrong"})
        assert response.status_code == 429
        assert "second" in response.json()["detail"]

    def test_attempts_reset_after_successful_login(self, client):
        """A successful login clears the failure counter."""
        client.post("/api/auth/login", json={"password": "wrong"})
        client.post("/api/auth/login", json={"password": "correctpassword"})

        response = client.post("/api/auth/login", json={"password": "wrong"})
        assert response.status_code == 401
        assert response.json()["detail"]["attempts_remaining"] == 4

    def test_login_missing_password(self, client):
        response = client.post("/api/auth/login", json={})
        assert response.status_code == 422

    def test_lockout_after_max_attempts(self, client):
        for _ in range(5):
            client.post("/api/auth/login", json={"password": "wrong"})

        # Even correct password is rejected during lockout
        response = client.post("/api/auth/login", json={"password": "correctpassword"})
        assert response.status_code == 429

    def test_xff_header_ignored(self, client):
        """X-Forwarded-For is ignored — rate limit uses socket IP only."""
        for _ in range(5):
            client.post(
                "/api/auth/login",
                json={"password": "wrong"},
                headers={"X-Forwarded-For": "1.2.3.4"},
            )

        # Spoofing a different X-Forwarded-For should NOT bypass lockout
        response = client.post(
            "/api/auth/login",
            json={"password": "correctpassword"},
            headers={"X-Forwarded-For": "5.6.7.8"},
        )
        assert response.status_code == 429


class TestProtectedEndpoints:
    """Test that endpoints require valid JWT."""

    def _get_token(self, client) -> str:
        response = client.post("/api/auth/login", json={"password": "correctpassword"})
        return response.json()["access_token"]

    def test_health_is_public(self, client):
        """Health endpoint should NOT require auth."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_protected_endpoint_without_token(self, client):
        """Accessing a protected endpoint without token returns 401."""
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_protected_endpoint_with_valid_token(self, client):
        token = self._get_token(client)
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["authenticated"] is True

    def test_protected_endpoint_with_invalid_token(self, client):
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401

    def test_protected_endpoint_with_expired_token(self, client, _env_vars, monkeypatch):
        """Expired tokens should be rejected."""
        from api import auth

        # Create a token that's already expired
        token = auth.create_access_token("user", expires_minutes=-1)
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401
