"""Tests for the scheduling module (Task 21).

Tests verify:
- Scheduler module is importable
- Pipeline runner functions exist and are callable
- Schedule configuration builds correct job list
- Pipeline runner handles subprocess success
- Pipeline runner handles subprocess failure
- Default schedule has enhance, suggest, learn jobs
"""

from pathlib import Path
from unittest.mock import MagicMock, patch


class TestSchedulerModuleExists:
    def test_module_importable(self) -> None:
        from content_engine.scheduler import build_schedule, run_pipeline

        assert callable(build_schedule)
        assert callable(run_pipeline)


class TestRunPipeline:
    """Test the generic pipeline runner."""

    @patch("content_engine.scheduler.subprocess.run")
    def test_success_returns_true(self, mock_run: MagicMock) -> None:
        from content_engine.scheduler import run_pipeline

        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        result = run_pipeline("enhance")
        assert result is True

    @patch("content_engine.scheduler.subprocess.run")
    def test_failure_returns_false(self, mock_run: MagicMock) -> None:
        from content_engine.scheduler import run_pipeline

        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        result = run_pipeline("enhance")
        assert result is False

    @patch("content_engine.scheduler.subprocess.run")
    def test_calls_correct_script(self, mock_run: MagicMock) -> None:
        from content_engine.scheduler import run_pipeline

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        run_pipeline("suggest")
        args = mock_run.call_args[0][0]
        assert "run_suggest.py" in args[-1]

    @patch("content_engine.scheduler.subprocess.run")
    def test_exception_returns_false(self, mock_run: MagicMock) -> None:
        from content_engine.scheduler import run_pipeline

        mock_run.side_effect = OSError("not found")
        result = run_pipeline("enhance")
        assert result is False


class TestBuildSchedule:
    """Test schedule configuration."""

    def test_returns_schedule_with_three_jobs(self) -> None:
        from content_engine.scheduler import build_schedule

        sched = build_schedule()
        assert len(sched.get_jobs()) == 3

    def test_job_tags_include_all_pipelines(self) -> None:
        from content_engine.scheduler import build_schedule

        sched = build_schedule()
        tags = set()
        for job in sched.get_jobs():
            tags.update(job.tags)
        assert "enhance" in tags
        assert "suggest" in tags
        assert "learn" in tags

    def test_custom_intervals(self) -> None:
        from content_engine.scheduler import build_schedule

        sched = build_schedule(
            enhance_minutes=15,
            suggest_day="monday",
            suggest_time="10:00",
            learn_time="07:00",
        )
        assert len(sched.get_jobs()) == 3


class TestScriptPaths:
    """Verify pipeline script files exist."""

    def test_enhance_script_exists(self) -> None:
        assert Path("src/content_engine/scripts/run_enhance.py").exists()

    def test_suggest_script_exists(self) -> None:
        assert Path("src/content_engine/scripts/run_suggest.py").exists()

    def test_learn_script_exists(self) -> None:
        assert Path("src/content_engine/scripts/run_learn.py").exists()
