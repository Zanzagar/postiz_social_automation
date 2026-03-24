"""Tests for embedding search with sqlite-vec fallback."""

import sqlite3

from content_engine.embeddings import (
    VEC_AVAILABLE,
    _vec_search,
    is_vec_available,
)


class TestVecAvailability:
    def test_detection_returns_bool(self):
        assert isinstance(is_vec_available(), bool)

    def test_module_level_flag(self):
        assert isinstance(VEC_AVAILABLE, bool)


class TestVecSearch:
    def test_returns_empty_when_unavailable(self, tmp_path):
        """When sqlite-vec can't load, returns empty results."""
        db = tmp_path / "test.db"
        conn = sqlite3.connect(str(db))
        conn.execute("""
            CREATE TABLE web_knowledge (
                id INTEGER PRIMARY KEY,
                content TEXT,
                pillar TEXT,
                fact_type TEXT
            )
        """)
        conn.execute("INSERT INTO web_knowledge VALUES (1, 'test', 'Cow Life', 'fact')")
        conn.commit()
        conn.close()

        results = _vec_search(str(db), "test query")
        # If vec isn't available, should return empty gracefully
        if not VEC_AVAILABLE:
            assert results == []

    def test_respects_env_var_disable(self, tmp_path, monkeypatch):
        """SQLITE_VEC_ENABLED=false disables vec search."""
        monkeypatch.setenv("SQLITE_VEC_ENABLED", "false")
        db = tmp_path / "test.db"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE dummy (id INTEGER)")
        conn.commit()
        conn.close()

        results = _vec_search(str(db), "test")
        assert results == []

    def test_returns_list_type(self, tmp_path):
        db = tmp_path / "test.db"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE dummy (id INTEGER)")
        conn.commit()
        conn.close()

        result = _vec_search(str(db), "query")
        assert isinstance(result, list)
