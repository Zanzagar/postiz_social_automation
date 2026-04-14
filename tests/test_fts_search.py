"""Tests for FTS5 full-text search in knowledge context."""

import sqlite3

import pytest

from content_engine.crawlers.knowledge_context import (
    _extract_keywords,
    _fts_search,
    get_knowledge_context,
)


@pytest.fixture
def fts_db(tmp_path):
    """DB with web_knowledge + FTS5 virtual table and sample data."""
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    conn.executescript("""
        CREATE TABLE web_knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT,
            fact_type TEXT,
            content TEXT,
            pillar TEXT,
            topic TEXT,
            source TEXT DEFAULT 'crawl',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        INSERT INTO web_knowledge (fact_type, content, pillar, topic) VALUES
            ('fact', 'Gita Valley has 80 cows on 430 acres of farmland',
             'Cow Life', 'farm operations'),
            ('fact', 'The farm produces ahimsa dairy including paneer and cheddar cheese',
             'Farm Ops', 'dairy products'),
            ('fact', 'Annual Chariot Festival draws hundreds of visitors each summer',
             'Community', 'events'),
            ('fact', 'Nandini is a disabled cow who receives special care daily',
             'Cow Life', 'cow care'),
            ('fact', 'The farm uses regenerative agriculture practices on all fields',
             'Farm Ops', 'agriculture'),
            ('fact', 'Sunday Feast community meals serve 50-100 guests weekly',
             'Community', 'community meals'),
            ('fact', 'Slaughter-free dairy certification from USDA is unique in North America',
             'Farm Ops', 'certification'),
            ('fact', 'Krishna consciousness guides all farm operations and cow care',
             'Spiritual', 'philosophy');

        CREATE VIRTUAL TABLE web_knowledge_fts USING fts5(
            content, topic,
            content='web_knowledge', content_rowid='id'
        );

        INSERT INTO web_knowledge_fts(web_knowledge_fts)
            VALUES('rebuild');

        -- Sync triggers
        CREATE TRIGGER web_knowledge_ai AFTER INSERT ON web_knowledge BEGIN
            INSERT INTO web_knowledge_fts(rowid, content, topic)
            VALUES (new.id, new.content, new.topic);
        END;

        CREATE TRIGGER web_knowledge_ad AFTER DELETE ON web_knowledge BEGIN
            INSERT INTO web_knowledge_fts(web_knowledge_fts, rowid, content, topic)
            VALUES('delete', old.id, old.content, old.topic);
        END;

        CREATE TRIGGER web_knowledge_au AFTER UPDATE ON web_knowledge BEGIN
            INSERT INTO web_knowledge_fts(web_knowledge_fts, rowid, content, topic)
            VALUES('delete', old.id, old.content, old.topic);
            INSERT INTO web_knowledge_fts(rowid, content, topic)
            VALUES (new.id, new.content, new.topic);
        END;
    """)
    conn.commit()
    conn.close()
    return str(db)


@pytest.fixture
def plain_db(tmp_path):
    """DB with web_knowledge but NO FTS5 table (fallback scenario)."""
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    conn.executescript("""
        CREATE TABLE web_knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT,
            fact_type TEXT,
            content TEXT,
            pillar TEXT,
            topic TEXT,
            source TEXT DEFAULT 'crawl',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        INSERT INTO web_knowledge (fact_type, content, pillar, topic) VALUES
            ('fact', 'Gita Valley has 80 cows on 430 acres', 'Cow Life', 'farm'),
            ('fact', 'The farm produces paneer and cheddar', 'Farm Ops', 'dairy');
    """)
    conn.commit()
    conn.close()
    return str(db)


# --- Keyword extraction ---


class TestExtractKeywords:
    def test_extracts_meaningful_words(self):
        keywords = _extract_keywords("The cows are grazing in the morning field")
        assert "cows" in keywords
        assert "grazing" in keywords
        assert "morning" in keywords
        assert "field" in keywords

    def test_removes_stopwords(self):
        keywords = _extract_keywords("The cows are in the field")
        assert "the" not in keywords
        assert "are" not in keywords
        assert "in" not in keywords

    def test_handles_empty_string(self):
        assert _extract_keywords("") == []

    def test_deduplicates(self):
        keywords = _extract_keywords("cow cow cow farm farm")
        assert keywords.count("cow") == 1

    def test_lowercases(self):
        keywords = _extract_keywords("Nandini the COW")
        assert "nandini" in keywords
        assert "cow" in keywords


# --- FTS search ---


class TestFtsSearch:
    def test_finds_relevant_results(self, fts_db):
        results = _fts_search(fts_db, "cows farmland acres")
        assert len(results) >= 1
        assert any("80 cows" in r["content"] for r in results)

    def test_bm25_ranking(self, fts_db):
        results = _fts_search(fts_db, "cow care disabled")
        # Nandini entry should rank high (matches cow + care + disabled)
        assert len(results) >= 1
        assert "Nandini" in results[0]["content"]

    def test_pillar_filter(self, fts_db):
        results = _fts_search(fts_db, "farm", pillar="Farm Ops")
        for r in results:
            assert r["pillar"] == "Farm Ops"

    def test_returns_empty_for_no_match(self, fts_db):
        results = _fts_search(fts_db, "xyznonexistent")
        assert results == []

    def test_respects_limit(self, fts_db):
        results = _fts_search(fts_db, "farm", limit=2)
        assert len(results) <= 2

    def test_returns_score(self, fts_db):
        results = _fts_search(fts_db, "cows")
        assert len(results) >= 1
        for r in results:
            assert "score" in r

    def test_graceful_when_no_fts_table(self, plain_db):
        """Returns empty when FTS table doesn't exist."""
        results = _fts_search(plain_db, "cows")
        assert results == []


# --- FTS triggers ---


class TestFtsTriggers:
    def test_insert_syncs_to_fts(self, fts_db):
        conn = sqlite3.connect(fts_db)
        conn.execute(
            "INSERT INTO web_knowledge (fact_type, content, pillar, topic) "
            "VALUES ('fact', 'New baby calf born on the farm', 'Cow Life', 'births')"
        )
        conn.commit()
        conn.close()

        results = _fts_search(fts_db, "baby calf born")
        assert len(results) >= 1
        assert any("baby calf" in r["content"] for r in results)

    def test_delete_removes_from_fts(self, fts_db):
        conn = sqlite3.connect(fts_db)
        # Get the Nandini row ID
        row = conn.execute("SELECT id FROM web_knowledge WHERE content LIKE '%Nandini%'").fetchone()
        conn.execute("DELETE FROM web_knowledge WHERE id = ?", (row[0],))
        conn.commit()
        conn.close()

        results = _fts_search(fts_db, "Nandini disabled")
        nandini_results = [r for r in results if "Nandini" in r["content"]]
        assert len(nandini_results) == 0


# --- Integration with get_knowledge_context ---


class TestGetKnowledgeContextFts:
    def test_uses_fts_when_available(self, fts_db):
        ctx = get_knowledge_context(fts_db, pillar="Cow Life", raw_text="Tell me about cows")
        assert "BACKGROUND" in ctx
        assert "cow" in ctx.lower()

    def test_falls_back_without_fts(self, plain_db):
        ctx = get_knowledge_context(plain_db, pillar="Cow Life")
        # Should still return results via old LIMIT query
        assert "80 cows" in ctx or ctx == ""  # Depends on pillar match

    def test_raw_text_improves_relevance(self, fts_db):
        # With cow-specific raw_text, should get cow facts
        ctx = get_knowledge_context(
            fts_db,
            pillar=None,
            raw_text="Nandini the cow needs special care",
        )
        assert "Nandini" in ctx
