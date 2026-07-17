"""Tests for the social_history pillar backfill script (mocked Claude CLI)."""

import json
import sqlite3
from unittest.mock import patch

import pytest

from content_engine.scripts import backfill_history_pillars as script

SCHEMA = """
    CREATE TABLE social_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT NOT NULL,
        external_id TEXT NOT NULL,
        post_text TEXT,
        media_urls TEXT,
        hashtags TEXT,
        posted_at DATETIME,
        likes INTEGER DEFAULT 0,
        comments INTEGER DEFAULT 0,
        shares INTEGER DEFAULT 0,
        reach INTEGER DEFAULT 0,
        pillar TEXT,
        imported_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(platform, external_id)
    );
    CREATE TABLE pillars (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(100) UNIQUE NOT NULL,
        description TEXT,
        color VARCHAR(20),
        is_active BOOLEAN DEFAULT 1,
        sort_order INTEGER DEFAULT 0,
        target_distribution FLOAT
    );
"""


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = tmp_path / "gvsa.db"
    conn = sqlite3.connect(str(path))
    conn.executescript(SCHEMA)
    conn.executescript("""
        INSERT INTO pillars (name, is_active, sort_order) VALUES ('Cow Life', 1, 1);
        INSERT INTO pillars (name, is_active, sort_order) VALUES ('Community', 1, 2);
        INSERT INTO pillars (name, is_active, sort_order) VALUES ('Old Retired Pillar', 0, 3);
    """)
    conn.commit()
    conn.close()
    monkeypatch.setenv("DATABASE_PATH", str(path))
    return str(path)


def _seed_rows(db_path, rows):
    """rows: list of (external_id, post_text, pillar)."""
    conn = sqlite3.connect(db_path)
    for ext_id, text, pillar in rows:
        conn.execute(
            "INSERT INTO social_history (platform, external_id, post_text, pillar)"
            " VALUES ('facebook', ?, ?, ?)",
            (ext_id, text, pillar),
        )
    conn.commit()
    conn.close()


def _pillars_by_ext(db_path):
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT external_id, pillar FROM social_history").fetchall()
    conn.close()
    return dict(rows)


class TestFetchActivePillars:
    def test_returns_only_active_pillars(self, db):
        conn = sqlite3.connect(db)
        assert script.fetch_active_pillars(conn) == ["Cow Life", "Community"]
        conn.close()

    def test_empty_when_no_active(self, tmp_path):
        path = tmp_path / "no_pillars.db"
        conn = sqlite3.connect(str(path))
        conn.executescript(SCHEMA)
        assert script.fetch_active_pillars(conn) == []
        conn.close()


class TestMain:
    def test_classifies_null_rows_with_active_pillar_names(self, db):
        _seed_rows(
            db,
            [
                ("fb_1", "Our cows enjoyed fresh hay at sunrise today", None),
                ("fb_2", "Sunday feast gathering with the whole community", None),
                ("fb_3", "Already classified post about festivals", "Community"),
            ],
        )
        prompts = []

        def fake_claude(prompt):
            prompts.append(prompt)
            ids = [
                int(line.split("]")[0][1:]) for line in prompt.splitlines() if line.startswith("[")
            ]
            return json.dumps(
                [{"id": ids[0], "pillar": "Cow Life"}, {"id": ids[1], "pillar": "Community"}]
            )

        with patch.object(script, "_call_claude", side_effect=fake_claude):
            script.main([])

        result = _pillars_by_ext(db)
        assert result["fb_1"] == "Cow Life"
        assert result["fb_2"] == "Community"
        assert result["fb_3"] == "Community"  # untouched
        # Prompt carries the ACTIVE pillar names from the DB, never the retired one
        assert "Cow Life" in prompts[0]
        assert "Community" in prompts[0]
        assert "Old Retired Pillar" not in prompts[0]

    def test_invalid_pillar_name_left_null(self, db):
        _seed_rows(db, [("fb_1", "A post about something quite unclassifiable", None)])

        def fake_claude(prompt):
            ids = [
                int(line.split("]")[0][1:]) for line in prompt.splitlines() if line.startswith("[")
            ]
            return json.dumps([{"id": ids[0], "pillar": "Made Up Pillar"}])

        with patch.object(script, "_call_claude", side_effect=fake_claude):
            script.main([])

        assert _pillars_by_ext(db)["fb_1"] is None

    def test_omitted_rows_left_null(self, db):
        _seed_rows(db, [("fb_1", "Completely ambiguous text that fits nothing here", None)])
        with patch.object(script, "_call_claude", return_value="[]"):
            script.main([])
        assert _pillars_by_ext(db)["fb_1"] is None

    def test_batches_of_up_to_ten_posts(self, db):
        _seed_rows(
            db, [(f"fb_{i}", f"Post number {i} about our lovely cows", None) for i in range(25)]
        )
        prompts = []

        def fake_claude(prompt):
            prompts.append(prompt)
            return "[]"

        with patch.object(script, "_call_claude", side_effect=fake_claude):
            script.main([])

        assert len(prompts) == 3  # 10 + 10 + 5
        for prompt in prompts:
            n_items = sum(1 for line in prompt.splitlines() if line.startswith("["))
            assert n_items <= script.BATCH_SIZE

    def test_limit_flag_caps_rows(self, db):
        _seed_rows(
            db, [(f"fb_{i}", f"Post number {i} about our lovely cows", None) for i in range(15)]
        )
        prompts = []

        def fake_claude(prompt):
            prompts.append(prompt)
            return "[]"

        with patch.object(script, "_call_claude", side_effect=fake_claude):
            script.main(["--limit", "5"])

        total_items = sum(1 for p in prompts for line in p.splitlines() if line.startswith("["))
        assert total_items == 5

    def test_dry_run_writes_nothing(self, db):
        _seed_rows(db, [("fb_1", "Our cows enjoyed fresh hay at sunrise today", None)])

        def fake_claude(prompt):
            ids = [
                int(line.split("]")[0][1:]) for line in prompt.splitlines() if line.startswith("[")
            ]
            return json.dumps([{"id": ids[0], "pillar": "Cow Life"}])

        with patch.object(script, "_call_claude", side_effect=fake_claude):
            script.main(["--dry-run"])

        assert _pillars_by_ext(db)["fb_1"] is None

    def test_cli_failure_leaves_rows_null(self, db):
        _seed_rows(db, [("fb_1", "Our cows enjoyed fresh hay at sunrise today", None)])
        with patch.object(script, "_call_claude", side_effect=RuntimeError("Claude CLI failed")):
            script.main([])  # must not raise
        assert _pillars_by_ext(db)["fb_1"] is None

    def test_markdown_fences_stripped(self, db):
        _seed_rows(db, [("fb_1", "Our cows enjoyed fresh hay at sunrise today", None)])

        def fake_claude(prompt):
            ids = [
                int(line.split("]")[0][1:]) for line in prompt.splitlines() if line.startswith("[")
            ]
            return f'```json\n[{{"id": {ids[0]}, "pillar": "Cow Life"}}]\n```'

        with patch.object(script, "_call_claude", side_effect=fake_claude):
            script.main([])

        assert _pillars_by_ext(db)["fb_1"] == "Cow Life"

    def test_no_active_pillars_makes_no_cli_calls(self, tmp_path, monkeypatch):
        path = tmp_path / "no_pillars.db"
        conn = sqlite3.connect(str(path))
        conn.executescript(SCHEMA)
        conn.execute(
            "INSERT INTO social_history (platform, external_id, post_text)"
            " VALUES ('facebook', 'fb_1', 'Some post text worth classifying')"
        )
        conn.commit()
        conn.close()
        monkeypatch.setenv("DATABASE_PATH", str(path))

        with patch.object(script, "_call_claude") as mock_claude:
            script.main([])
        mock_claude.assert_not_called()

    def test_nothing_to_classify_makes_no_cli_calls(self, db):
        _seed_rows(db, [("fb_1", "Already classified post about the cows", "Cow Life")])
        with patch.object(script, "_call_claude") as mock_claude:
            script.main([])
        mock_claude.assert_not_called()


class TestCliCallContract:
    """The contract pins the Claude CLI call shape (cwd=/tmp, 120s, 3 concurrent)."""

    def test_constants(self):
        assert script.BATCH_SIZE == 10
        assert script.CLI_TIMEOUT == 120
        assert script.MAX_CONCURRENT == 3

    def test_call_claude_uses_clean_cwd_and_timeout(self):
        with patch.object(script.subprocess, "run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "[]"
            script._call_claude("prompt")
        _, kwargs = mock_run.call_args
        assert kwargs["cwd"] == "/tmp"
        assert kwargs["timeout"] == 120
