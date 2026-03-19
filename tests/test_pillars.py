"""Tests for dynamic pillar loading from SQLite."""

import sqlite3
import tempfile
from pathlib import Path

from content_engine.pillars import _FALLBACK_PILLARS, get_active_pillar_names


class TestGetActivePillarNames:
    def test_returns_fallback_when_no_db(self):
        result = get_active_pillar_names(Path("/nonexistent/db.sqlite"))
        assert result == list(_FALLBACK_PILLARS)

    def test_returns_fallback_when_no_pillars_table(self):
        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            conn = sqlite3.connect(f.name)
            conn.execute("CREATE TABLE dummy (id INTEGER)")
            conn.close()
            result = get_active_pillar_names(Path(f.name))
            assert result == list(_FALLBACK_PILLARS)

    def test_returns_active_pillars_from_db(self):
        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            conn = sqlite3.connect(f.name)
            conn.execute(
                "CREATE TABLE pillars (id INTEGER PRIMARY KEY, name TEXT, is_active INTEGER, sort_order INTEGER)"
            )
            conn.execute("INSERT INTO pillars VALUES (1, 'Alpha', 1, 0)")
            conn.execute("INSERT INTO pillars VALUES (2, 'Beta', 1, 1)")
            conn.execute("INSERT INTO pillars VALUES (3, 'Gamma', 0, 2)")  # inactive
            conn.commit()
            conn.close()
            result = get_active_pillar_names(Path(f.name))
            assert result == ["Alpha", "Beta"]

    def test_returns_fallback_when_all_inactive(self):
        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            conn = sqlite3.connect(f.name)
            conn.execute(
                "CREATE TABLE pillars (id INTEGER PRIMARY KEY, name TEXT, is_active INTEGER, sort_order INTEGER)"
            )
            conn.execute("INSERT INTO pillars VALUES (1, 'Alpha', 0, 0)")
            conn.commit()
            conn.close()
            result = get_active_pillar_names(Path(f.name))
            assert result == list(_FALLBACK_PILLARS)
