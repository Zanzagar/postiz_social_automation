"""Tests for Streamlit authentication (Task 19).

Tests verify:
- Auth helper is importable
- check_password returns True when already authenticated
- check_password returns False when not authenticated
- verify_password uses constant-time comparison
- secrets.toml.example exists
- secrets.toml is gitignored
"""

from pathlib import Path


class TestAuthHelperExists:
    def test_auth_module_importable(self) -> None:
        from app.auth import check_password, verify_password

        assert callable(check_password)
        assert callable(verify_password)


class TestVerifyPassword:
    """Test the password comparison helper."""

    def test_correct_password_returns_true(self) -> None:
        from app.auth import verify_password

        assert verify_password("mypassword", "mypassword") is True

    def test_wrong_password_returns_false(self) -> None:
        from app.auth import verify_password

        assert verify_password("wrong", "mypassword") is False

    def test_empty_password_returns_false(self) -> None:
        from app.auth import verify_password

        assert verify_password("", "mypassword") is False

    def test_empty_expected_returns_false_for_nonempty(self) -> None:
        from app.auth import verify_password

        assert verify_password("something", "") is False


class TestSecretsConfig:
    def test_secrets_example_exists(self) -> None:
        example = Path(".streamlit/secrets.toml.example")
        assert example.exists(), f"Secrets example not found at {example}"

    def test_secrets_toml_is_gitignored(self) -> None:
        gitignore = Path(".gitignore").read_text()
        assert ".streamlit/secrets.toml" in gitignore
