"""Tests for the Learning Pipeline (Task 17).

Tests verify:
- Pulls analytics for posted rows with Postiz IDs
- Skips already-known post IDs (no duplicates)
- Saves merged performance data to disk
- Updates learning context via ContentIntelligence
- Handles Postiz API failures per-post gracefully
- PipelineResult counts are accurate
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from content_engine.models import (
    ContentPillar,
    ContentRow,
    ContentStatus,
    Platform,
    PostPerformance,
)
from content_engine.pipeline import learn_pipeline


class TestLearnPipeline:
    def _make_mocks(self):
        sheets = MagicMock()
        postiz = MagicMock()
        intelligence = MagicMock()
        return sheets, postiz, intelligence

    def _make_posted_row(self, row_number: int, postiz_ids: str) -> ContentRow:
        return ContentRow(
            row_number=row_number,
            date=datetime(2026, 2, 20),
            raw_text="Test post",
            platforms={Platform.INSTAGRAM: True},
            status=ContentStatus.POSTED,
            captions={Platform.INSTAGRAM: "IG caption"},
            postiz_ids=postiz_ids,
            content_pillar=ContentPillar.COW_LIFE,
        )

    def test_pulls_analytics_for_posted_rows(self, tmp_path: Path) -> None:
        sheets, postiz, intelligence = self._make_mocks()

        row = self._make_posted_row(2, "post_1")
        sheets.get_rows_by_status.return_value = [row]

        perf = PostPerformance(
            post_id="post_1",
            platform=Platform.INSTAGRAM,
            pillar=ContentPillar.COW_LIFE,
            posted_at=datetime(2026, 2, 20),
            likes=50,
            comments=10,
        )
        postiz.get_post_analytics.return_value = perf

        result = learn_pipeline(
            sheets=sheets,
            postiz=postiz,
            intelligence=intelligence,
            data_dir=tmp_path,
        )

        postiz.get_post_analytics.assert_called_once_with("post_1", ContentPillar.COW_LIFE)
        assert result.processed == 1

    def test_skips_already_known_post_ids(self, tmp_path: Path) -> None:
        sheets, postiz, intelligence = self._make_mocks()

        # Pre-populate performance file with post_1
        perf_file = tmp_path / "post-performance.json"
        perf_file.write_text(
            json.dumps(
                [
                    {
                        "post_id": "post_1",
                        "platform": "instagram",
                        "pillar": "Cow Life",
                        "posted_at": "2026-02-20T00:00:00",
                        "likes": 50,
                    }
                ]
            )
        )

        row = self._make_posted_row(2, "post_1")
        sheets.get_rows_by_status.return_value = [row]

        result = learn_pipeline(
            sheets=sheets,
            postiz=postiz,
            intelligence=intelligence,
            data_dir=tmp_path,
        )

        postiz.get_post_analytics.assert_not_called()
        assert result.skipped == 1

    def test_handles_multiple_postiz_ids_per_row(self, tmp_path: Path) -> None:
        sheets, postiz, intelligence = self._make_mocks()

        row = self._make_posted_row(2, "post_1,post_2")
        sheets.get_rows_by_status.return_value = [row]

        perf = PostPerformance(
            post_id="post_1",
            platform=Platform.INSTAGRAM,
            pillar=ContentPillar.COW_LIFE,
            posted_at=datetime(2026, 2, 20),
        )
        postiz.get_post_analytics.return_value = perf

        result = learn_pipeline(
            sheets=sheets,
            postiz=postiz,
            intelligence=intelligence,
            data_dir=tmp_path,
        )

        assert postiz.get_post_analytics.call_count == 2
        assert result.processed == 2

    def test_saves_performance_data_to_disk(self, tmp_path: Path) -> None:
        sheets, postiz, intelligence = self._make_mocks()

        row = self._make_posted_row(2, "post_1")
        sheets.get_rows_by_status.return_value = [row]

        perf = PostPerformance(
            post_id="post_1",
            platform=Platform.INSTAGRAM,
            pillar=ContentPillar.COW_LIFE,
            posted_at=datetime(2026, 2, 20),
            likes=50,
            comments=10,
        )
        postiz.get_post_analytics.return_value = perf

        learn_pipeline(
            sheets=sheets,
            postiz=postiz,
            intelligence=intelligence,
            data_dir=tmp_path,
        )

        perf_file = tmp_path / "post-performance.json"
        assert perf_file.exists()
        data = json.loads(perf_file.read_text())
        assert len(data) == 1
        assert data[0]["post_id"] == "post_1"
        assert data[0]["likes"] == 50

    def test_updates_learning_context(self, tmp_path: Path) -> None:
        sheets, postiz, intelligence = self._make_mocks()
        sheets.get_rows_by_status.return_value = []

        learn_pipeline(
            sheets=sheets,
            postiz=postiz,
            intelligence=intelligence,
            data_dir=tmp_path,
        )

        intelligence.save_learning_context.assert_called_once()

    def test_continues_after_api_failure(self, tmp_path: Path) -> None:
        sheets, postiz, intelligence = self._make_mocks()

        row = self._make_posted_row(2, "post_1,post_2")
        sheets.get_rows_by_status.return_value = [row]

        perf = PostPerformance(
            post_id="post_2",
            platform=Platform.INSTAGRAM,
            pillar=ContentPillar.COW_LIFE,
            posted_at=datetime(2026, 2, 20),
        )
        postiz.get_post_analytics.side_effect = [
            Exception("API error"),
            perf,
        ]

        result = learn_pipeline(
            sheets=sheets,
            postiz=postiz,
            intelligence=intelligence,
            data_dir=tmp_path,
        )

        assert result.processed == 1
        assert result.errors == 1

    def test_handles_no_posted_rows(self, tmp_path: Path) -> None:
        sheets, postiz, intelligence = self._make_mocks()
        sheets.get_rows_by_status.return_value = []

        result = learn_pipeline(
            sheets=sheets,
            postiz=postiz,
            intelligence=intelligence,
            data_dir=tmp_path,
        )

        assert result.processed == 0
        assert result.errors == 0
        postiz.get_post_analytics.assert_not_called()

    def test_handles_rows_without_postiz_ids(self, tmp_path: Path) -> None:
        sheets, postiz, intelligence = self._make_mocks()

        row = ContentRow(
            row_number=2,
            date=datetime(2026, 2, 20),
            raw_text="Test",
            platforms={Platform.INSTAGRAM: True},
            status=ContentStatus.POSTED,
            captions={},
            postiz_ids=None,
        )
        sheets.get_rows_by_status.return_value = [row]

        result = learn_pipeline(
            sheets=sheets,
            postiz=postiz,
            intelligence=intelligence,
            data_dir=tmp_path,
        )

        assert result.skipped == 1
        postiz.get_post_analytics.assert_not_called()


class TestRunLearnScript:
    def test_main_is_callable(self) -> None:
        from content_engine.scripts.run_learn import main

        assert callable(main)
