"""Tests for Docker configuration (Task 20).

Tests verify:
- Dockerfile exists and has correct base image
- docker-compose.yaml includes content-hub and content-engine services
- .dockerignore exists with proper exclusions
"""

from pathlib import Path


class TestDockerfileExists:
    def test_dockerfile_exists(self) -> None:
        assert Path("Dockerfile").exists()

    def test_dockerfile_uses_python_311(self) -> None:
        content = Path("Dockerfile").read_text()
        assert "python:3.11-slim" in content

    def test_dockerfile_exposes_streamlit_port(self) -> None:
        content = Path("Dockerfile").read_text()
        assert "EXPOSE 8501" in content

    def test_dockerfile_installs_project(self) -> None:
        content = Path("Dockerfile").read_text()
        assert "pip install" in content


class TestDockerComposeServices:
    """Verify docker-compose.yaml has content-hub and content-engine services."""

    def _read_compose(self) -> str:
        return Path("docker-compose.yaml").read_text()

    def test_content_hub_service_exists(self) -> None:
        assert "content-hub:" in self._read_compose()

    def test_content_engine_service_exists(self) -> None:
        assert "content-engine:" in self._read_compose()

    def test_content_hub_exposes_8501(self) -> None:
        assert "8501:8501" in self._read_compose()

    def test_content_engine_runs_scheduler(self) -> None:
        content = self._read_compose()
        assert "scheduler" in content

    def test_services_use_env_file(self) -> None:
        content = self._read_compose()
        # Both services should reference .env
        assert content.count("env_file:") >= 3  # postiz + hub + engine


class TestDockerIgnore:
    def test_dockerignore_exists(self) -> None:
        assert Path(".dockerignore").exists()

    def test_dockerignore_excludes_venv(self) -> None:
        content = Path(".dockerignore").read_text()
        assert ".venv" in content

    def test_dockerignore_excludes_git(self) -> None:
        content = Path(".dockerignore").read_text()
        assert ".git" in content
