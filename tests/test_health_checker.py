"""Tests for health_checker.py - Docker service health checker."""

from unittest.mock import MagicMock, patch

from health_checker import HealthChecker, HealthResult, HealthStatus, SERVICE_CONTAINERS


class TestHealthStatus:
    def test_enum_values(self):
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.MISSING.value == "missing"


class TestHealthResult:
    def test_dataclass_creation(self):
        result = HealthResult(
            service_name="postiz",
            status=HealthStatus.HEALTHY,
            response_time_ms=42,
            details={"docker_health": "healthy"},
        )
        assert result.service_name == "postiz"
        assert result.status == HealthStatus.HEALTHY
        assert result.response_time_ms == 42
        assert result.details == {"docker_health": "healthy"}

    def test_details_defaults_to_none(self):
        result = HealthResult(
            service_name="redis",
            status=HealthStatus.UNHEALTHY,
            response_time_ms=10,
        )
        assert result.details is None


class TestServiceContainers:
    def test_all_seven_services_defined(self):
        assert len(SERVICE_CONTAINERS) == 7

    def test_expected_services_present(self):
        expected = {
            "postiz",
            "postiz-postgres",
            "postiz-redis",
            "temporal",
            "temporal-postgresql",
            "temporal-elasticsearch",
            "temporal-ui",
        }
        assert set(SERVICE_CONTAINERS.keys()) == expected


class TestHealthCheckerInit:
    @patch("health_checker.docker")
    def test_init_connects_to_docker(self, mock_docker):
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client

        checker = HealthChecker()

        mock_docker.from_env.assert_called_once()
        mock_client.ping.assert_called_once()

    @patch("health_checker.docker")
    def test_init_raises_on_docker_unavailable(self, mock_docker):
        import docker as docker_mod

        mock_docker.from_env.side_effect = Exception("connection refused")
        mock_docker.errors.DockerException = Exception

        import pytest

        with pytest.raises(RuntimeError, match="Cannot connect to Docker"):
            HealthChecker()


class TestCheckService:
    @patch("health_checker.docker")
    def test_missing_container_returns_missing(self, mock_docker):
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        mock_docker.errors.DockerException = Exception
        mock_docker.errors.NotFound = type("NotFound", (Exception,), {})
        mock_docker.errors.APIError = type("APIError", (Exception,), {})
        mock_client.containers.get.side_effect = mock_docker.errors.NotFound("not found")

        checker = HealthChecker()
        result = checker.check_service("postiz", "postiz")

        assert result.status == HealthStatus.MISSING
        assert result.service_name == "postiz"
        assert "not found" in result.details["error"].lower()

    @patch("health_checker.docker")
    def test_stopped_container_returns_unhealthy(self, mock_docker):
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        mock_docker.errors.DockerException = Exception
        mock_docker.errors.NotFound = type("NotFound", (Exception,), {})
        mock_docker.errors.APIError = type("APIError", (Exception,), {})

        mock_container = MagicMock()
        mock_container.status = "exited"
        mock_client.containers.get.return_value = mock_container

        checker = HealthChecker()
        result = checker.check_service("postiz", "postiz")

        assert result.status == HealthStatus.UNHEALTHY
        assert "not running" in result.details["error"].lower()

    @patch("health_checker.docker")
    def test_healthy_container_returns_healthy(self, mock_docker):
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        mock_docker.errors.DockerException = Exception
        mock_docker.errors.NotFound = type("NotFound", (Exception,), {})
        mock_docker.errors.APIError = type("APIError", (Exception,), {})

        mock_container = MagicMock()
        mock_container.status = "running"
        mock_container.attrs = {"State": {"Health": {"Status": "healthy"}}}
        mock_client.containers.get.return_value = mock_container

        checker = HealthChecker()
        result = checker.check_service("postiz", "postiz")

        assert result.status == HealthStatus.HEALTHY
        assert result.details["docker_health"] == "healthy"

    @patch("health_checker.docker")
    def test_unhealthy_healthcheck_returns_unhealthy(self, mock_docker):
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        mock_docker.errors.DockerException = Exception
        mock_docker.errors.NotFound = type("NotFound", (Exception,), {})
        mock_docker.errors.APIError = type("APIError", (Exception,), {})

        mock_container = MagicMock()
        mock_container.status = "running"
        mock_container.attrs = {
            "State": {
                "Health": {
                    "Status": "unhealthy",
                    "Log": [{"Output": "connection refused"}],
                }
            }
        }
        mock_client.containers.get.return_value = mock_container

        checker = HealthChecker()
        result = checker.check_service("postiz", "postiz")

        assert result.status == HealthStatus.UNHEALTHY
        assert result.details["docker_health"] == "unhealthy"

    @patch("health_checker.docker")
    def test_no_healthcheck_running_container_is_healthy(self, mock_docker):
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        mock_docker.errors.DockerException = Exception
        mock_docker.errors.NotFound = type("NotFound", (Exception,), {})
        mock_docker.errors.APIError = type("APIError", (Exception,), {})

        mock_container = MagicMock()
        mock_container.status = "running"
        mock_container.attrs = {"State": {}}
        mock_client.containers.get.return_value = mock_container

        checker = HealthChecker()
        result = checker.check_service("postiz", "postiz")

        assert result.status == HealthStatus.HEALTHY
        assert result.details["docker_health"] == "none"


class TestCheckAllServices:
    @patch("health_checker.docker")
    def test_checks_all_seven_services(self, mock_docker):
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        mock_docker.errors.DockerException = Exception
        mock_docker.errors.NotFound = type("NotFound", (Exception,), {})
        mock_docker.errors.APIError = type("APIError", (Exception,), {})

        mock_container = MagicMock()
        mock_container.status = "running"
        mock_container.attrs = {"State": {"Health": {"Status": "healthy"}}}
        mock_client.containers.get.return_value = mock_container

        checker = HealthChecker()
        results = checker.check_all_services()

        assert len(results) == 7
        assert all(isinstance(r, HealthResult) for r in results)
        service_names = {r.service_name for r in results}
        assert service_names == set(SERVICE_CONTAINERS.keys())
