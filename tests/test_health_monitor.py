"""Tests for health_monitor.py - Main health monitor orchestrator."""

from unittest.mock import MagicMock, patch

from health_checker import HealthResult, HealthStatus
from health_monitor import run_once


class TestRunOnce:
    @patch("health_monitor.HealthNotifier")
    @patch("health_monitor.HealthStorage")
    @patch("health_monitor.HealthChecker")
    def test_returns_zero_when_all_healthy(self, MockChecker, MockStorage, MockNotifier):
        mock_checker = MagicMock()
        MockChecker.return_value = mock_checker
        mock_checker.check_all_services.return_value = [
            HealthResult("postiz", HealthStatus.HEALTHY, 10),
            HealthResult("postiz-redis", HealthStatus.HEALTHY, 5),
        ]
        mock_notifier = MagicMock()
        MockNotifier.return_value = mock_notifier
        mock_notifier.process_result.return_value = None

        exit_code = run_once(verbose=False)

        assert exit_code == 0

    @patch("health_monitor.HealthNotifier")
    @patch("health_monitor.HealthStorage")
    @patch("health_monitor.HealthChecker")
    def test_returns_one_when_unhealthy(self, MockChecker, MockStorage, MockNotifier):
        mock_checker = MagicMock()
        MockChecker.return_value = mock_checker
        mock_checker.check_all_services.return_value = [
            HealthResult("postiz", HealthStatus.HEALTHY, 10),
            HealthResult("postiz-redis", HealthStatus.UNHEALTHY, 100, {"error": "down"}),
        ]
        mock_notifier = MagicMock()
        MockNotifier.return_value = mock_notifier
        mock_notifier.process_result.return_value = None

        exit_code = run_once(verbose=False)

        assert exit_code == 1

    @patch("health_monitor.HealthChecker")
    def test_returns_two_on_docker_error(self, MockChecker):
        MockChecker.side_effect = RuntimeError("Cannot connect to Docker daemon")

        exit_code = run_once(verbose=False)

        assert exit_code == 2

    @patch("health_monitor.HealthNotifier")
    @patch("health_monitor.HealthStorage")
    @patch("health_monitor.HealthChecker")
    def test_processes_all_results_through_notifier(self, MockChecker, MockStorage, MockNotifier):
        mock_checker = MagicMock()
        MockChecker.return_value = mock_checker
        results = [
            HealthResult("postiz", HealthStatus.HEALTHY, 10),
            HealthResult("redis", HealthStatus.HEALTHY, 5),
            HealthResult("temporal", HealthStatus.MISSING, 0),
        ]
        mock_checker.check_all_services.return_value = results
        mock_notifier = MagicMock()
        MockNotifier.return_value = mock_notifier
        mock_notifier.process_result.return_value = None

        run_once(verbose=False)

        assert mock_notifier.process_result.call_count == 3

    @patch("health_monitor.HealthNotifier")
    @patch("health_monitor.HealthStorage")
    @patch("health_monitor.HealthChecker")
    def test_verbose_mode_does_not_crash(self, MockChecker, MockStorage, MockNotifier):
        mock_checker = MagicMock()
        MockChecker.return_value = mock_checker
        mock_checker.check_all_services.return_value = [
            HealthResult("postiz", HealthStatus.HEALTHY, 10),
        ]
        mock_notifier = MagicMock()
        MockNotifier.return_value = mock_notifier
        mock_notifier.process_result.return_value = 42

        exit_code = run_once(verbose=True)

        assert exit_code == 0
