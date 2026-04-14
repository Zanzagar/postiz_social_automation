"""Tests for preference pairs storage and retrieval."""

import sqlite3

from content_engine.preference_pairs import (
    get_preference_pairs,
    save_preference_pair,
)


def _create_db(path):
    conn = sqlite3.connect(str(path))
    conn.execute("""
        CREATE TABLE preference_pairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            original_text TEXT NOT NULL,
            edited_text TEXT NOT NULL,
            instruction TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    return str(path)


class TestSavePreferencePair:
    def test_saves_successfully(self, tmp_path):
        db = _create_db(tmp_path / "test.db")
        result = save_preference_pair(
            db, "original caption", "edited caption", "instagram", "make shorter"
        )
        assert result is True

        conn = sqlite3.connect(db)
        rows = conn.execute("SELECT * FROM preference_pairs").fetchall()
        conn.close()
        assert len(rows) == 1

    def test_graceful_when_no_table(self, tmp_path):
        db = str(tmp_path / "empty.db")
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE dummy (id INTEGER)")
        conn.commit()
        conn.close()

        result = save_preference_pair(db, "orig", "edited", "instagram")
        assert result is False


class TestGetPreferencePairs:
    def test_retrieves_by_platform(self, tmp_path):
        db = _create_db(tmp_path / "test.db")
        save_preference_pair(db, "a", "b", "instagram", "fix")
        save_preference_pair(db, "c", "d", "facebook", "improve")

        results = get_preference_pairs(db, platform="instagram")
        assert len(results) == 1
        assert results[0]["platform"] == "instagram"

    def test_retrieves_all(self, tmp_path):
        db = _create_db(tmp_path / "test.db")
        save_preference_pair(db, "a", "b", "instagram")
        save_preference_pair(db, "c", "d", "facebook")

        results = get_preference_pairs(db)
        assert len(results) == 2

    def test_respects_limit(self, tmp_path):
        db = _create_db(tmp_path / "test.db")
        for i in range(10):
            save_preference_pair(db, f"orig{i}", f"edit{i}", "instagram")

        results = get_preference_pairs(db, limit=3)
        assert len(results) == 3

    def test_returns_empty_when_no_table(self, tmp_path):
        db = str(tmp_path / "empty.db")
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE dummy (id INTEGER)")
        conn.commit()
        conn.close()

        results = get_preference_pairs(db)
        assert results == []

    def test_returns_dict_fields(self, tmp_path):
        db = _create_db(tmp_path / "test.db")
        save_preference_pair(db, "orig", "edited", "instagram", "shorten")

        results = get_preference_pairs(db)
        r = results[0]
        assert "original_text" in r
        assert "edited_text" in r
        assert "instruction" in r
        assert "platform" in r
