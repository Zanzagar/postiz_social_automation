"""Tests for Docker configuration (Task 20).

Tests verify:
- Dockerfile exists and has correct base image
- docker-compose.yaml includes content-hub service (content-engine runs on host)
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

    def test_dockerfile_sets_pythonpath(self) -> None:
        content = Path("Dockerfile").read_text()
        assert "PYTHONPATH" in content


class TestDockerComposeServices:
    """Verify docker-compose.yaml has content-hub service.

    content-engine runs on the host (not Docker) because it requires
    Claude CLI with OAuth authentication ($0/call via Max subscription).
    """

    def _read_compose(self) -> str:
        return Path("docker-compose.yaml").read_text()

    def test_content_hub_service_exists(self) -> None:
        assert "content-hub:" in self._read_compose()

    def test_content_hub_exposes_8501(self) -> None:
        assert "8501:8501" in self._read_compose()

    def test_content_engine_not_containerized(self) -> None:
        """content-engine requires Claude CLI and must run on the host."""
        content = self._read_compose()
        assert "content-engine:" not in content

    def test_content_engine_host_instructions_documented(self) -> None:
        """docker-compose.yaml should document how to run engine on host."""
        content = self._read_compose()
        assert "content-engine runs on the HOST" in content

    def test_content_hub_uses_env_file(self) -> None:
        content = self._read_compose()
        assert "env_file:" in content


class TestDockerIgnore:
    def test_dockerignore_exists(self) -> None:
        assert Path(".dockerignore").exists()

    def test_dockerignore_excludes_venv(self) -> None:
        content = Path(".dockerignore").read_text()
        assert ".venv" in content

    def test_dockerignore_excludes_git(self) -> None:
        content = Path(".dockerignore").read_text()
        assert ".git" in content
