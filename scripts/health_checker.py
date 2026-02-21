"""Docker service health checker for the Postiz stack."""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import docker


class HealthStatus(Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    MISSING = "missing"


@dataclass
class HealthResult:
    service_name: str
    status: HealthStatus
    response_time_ms: int
    details: Optional[dict] = None


SERVICE_CONTAINERS = {
    "postiz": "postiz",
    "postiz-postgres": "postiz-postgres",
    "postiz-redis": "postiz-redis",
    "temporal": "postiz-temporal",
    "temporal-postgresql": "postiz-temporal-postgres",
    "temporal-elasticsearch": "postiz-temporal-es",
    "temporal-ui": "postiz-temporal-ui",
}


class HealthChecker:
    def __init__(self):
        try:
            self.client = docker.from_env()
            self.client.ping()
        except docker.errors.DockerException as e:
            raise RuntimeError(f"Cannot connect to Docker daemon: {e}")

    def check_all_services(self) -> list[HealthResult]:
        results = []
        for service_name, container_name in SERVICE_CONTAINERS.items():
            result = self.check_service(service_name, container_name)
            results.append(result)
        return results

    def check_service(self, service_name: str, container_name: str) -> HealthResult:
        start = time.perf_counter()

        try:
            container = self.client.containers.get(container_name)
        except docker.errors.NotFound:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            return HealthResult(
                service_name=service_name,
                status=HealthStatus.MISSING,
                response_time_ms=elapsed_ms,
                details={"error": f"Container {container_name} not found"},
            )
        except docker.errors.APIError as e:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            return HealthResult(
                service_name=service_name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=elapsed_ms,
                details={"error": f"Docker API error: {e}"},
            )

        if container.status != "running":
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            return HealthResult(
                service_name=service_name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=elapsed_ms,
                details={"error": f"Container not running: {container.status}"},
            )

        health = container.attrs.get("State", {}).get("Health", {})
        health_status = health.get("Status")

        elapsed_ms = int((time.perf_counter() - start) * 1000)

        if health_status == "healthy":
            return HealthResult(
                service_name=service_name,
                status=HealthStatus.HEALTHY,
                response_time_ms=elapsed_ms,
                details={"docker_health": health_status},
            )
        elif health_status == "unhealthy":
            log = health.get("Log", [{}])[-1] if health.get("Log") else {}
            return HealthResult(
                service_name=service_name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=elapsed_ms,
                details={
                    "docker_health": health_status,
                    "last_output": log.get("Output", "")[:500],
                },
            )

        return HealthResult(
            service_name=service_name,
            status=HealthStatus.HEALTHY,
            response_time_ms=elapsed_ms,
            details={"docker_health": "none", "container_status": "running"},
        )
