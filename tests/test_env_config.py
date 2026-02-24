"""Tests for environment configuration completeness."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


class TestEnvExample:
    """Verify .env.example documents all required variables."""

    def test_env_example_exists(self):
        assert (PROJECT_ROOT / ".env.example").exists()

    def test_contains_postiz_api_key(self):
        content = (PROJECT_ROOT / ".env.example").read_text()
        assert "POSTIZ_API_KEY" in content

    def test_contains_google_credentials(self):
        content = (PROJECT_ROOT / ".env.example").read_text()
        assert "GOOGLE_CREDENTIALS_PATH" in content
        assert "SPREADSHEET_ID" in content

    def test_contains_streamlit_password(self):
        content = (PROJECT_ROOT / ".env.example").read_text()
        assert "STREAMLIT_PASSWORD" in content

    def test_no_real_secrets(self):
        """Ensure .env.example has only placeholder values."""
        content = (PROJECT_ROOT / ".env.example").read_text()
        for line in content.splitlines():
            if line.startswith("#") or not line.strip():
                continue
            if "=" in line:
                value = line.split("=", 1)[1].strip()
                # Should not contain actual API keys (long hex/base64 strings)
                # JWT_SECRET is a known default, allow it
                if "JWT_SECRET" in line:
                    continue
                assert len(value) < 80 or "your-" in value or "path" in value.lower(), (
                    f"Possible real secret in .env.example: {line[:50]}..."
                )
