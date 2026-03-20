"""Tests for crawl checkpoint and error handling."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from content_engine.crawlers.base import CrawlCheckpoint, CrawlResult


class TestCrawlCheckpoint:
    def test_save_and_load(self, tmp_path):
        cp = CrawlCheckpoint("gitavalley", data_dir=tmp_path)
        cp.save(last_url="https://gitavalley.com/page/5", processed_count=25)

        loaded = CrawlCheckpoint("gitavalley", data_dir=tmp_path)
        data = loaded.load()
        assert data["last_url"] == "https://gitavalley.com/page/5"
        assert data["processed_count"] == 25

    def test_load_missing_returns_empty(self, tmp_path):
        cp = CrawlCheckpoint("nonexistent", data_dir=tmp_path)
        data = cp.load()
        assert data == {}

    def test_save_overwrites(self, tmp_path):
        cp = CrawlCheckpoint("test", data_dir=tmp_path)
        cp.save(last_url="url1", processed_count=5)
        cp.save(last_url="url2", processed_count=10)

        data = cp.load()
        assert data["last_url"] == "url2"
        assert data["processed_count"] == 10

    def test_clear(self, tmp_path):
        cp = CrawlCheckpoint("test", data_dir=tmp_path)
        cp.save(last_url="url", processed_count=1)
        cp.clear()
        assert cp.load() == {}


class TestCrawlResult:
    def test_success_result(self):
        result = CrawlResult(source="gitavalley", total=10, succeeded=10, failed=0)
        assert result.is_success
        assert result.errors == []

    def test_partial_failure(self):
        result = CrawlResult(
            source="iskcon",
            total=10,
            succeeded=8,
            failed=2,
            errors=["HTTP 500 for /page1", "Timeout for /page2"],
        )
        assert not result.is_success
        assert len(result.errors) == 2

    def test_to_dict(self):
        result = CrawlResult(source="facebook", total=50, succeeded=50, failed=0)
        d = result.to_dict()
        assert d["source"] == "facebook"
        assert d["total"] == 50
        assert d["succeeded"] == 50
        assert d["failed"] == 0
        assert d["is_success"] is True
