"""Tests for periodic crawl and analytics scheduler."""

import json

import pytest

from content_engine.scheduler import CrawlScheduler


class TestCrawlSchedulerInit:
    def test_default_intervals(self):
        scheduler = CrawlScheduler(db_path="test.db")
        assert scheduler.web_crawl_interval_hours == 168  # weekly
        assert scheduler.analytics_sync_interval_hours == 24  # daily
        assert scheduler.hashtag_update_interval_hours == 24

    def test_custom_intervals(self):
        scheduler = CrawlScheduler(
            db_path="test.db",
            web_crawl_interval_hours=48,
            analytics_sync_interval_hours=12,
        )
        assert scheduler.web_crawl_interval_hours == 48
        assert scheduler.analytics_sync_interval_hours == 12


class TestShouldRun:
    def test_should_run_when_never_run(self, tmp_path):
        scheduler = CrawlScheduler(db_path=str(tmp_path / "test.db"), state_dir=tmp_path)
        assert scheduler.should_run("web_crawl") is True

    def test_should_not_run_when_recently_run(self, tmp_path):
        scheduler = CrawlScheduler(db_path=str(tmp_path / "test.db"), state_dir=tmp_path)
        scheduler.record_run("web_crawl")
        assert scheduler.should_run("web_crawl") is False


class TestRecordRun:
    def test_record_creates_timestamp(self, tmp_path):
        scheduler = CrawlScheduler(db_path=str(tmp_path / "test.db"), state_dir=tmp_path)
        scheduler.record_run("analytics_sync")
        state = scheduler._load_state()
        assert "analytics_sync" in state
