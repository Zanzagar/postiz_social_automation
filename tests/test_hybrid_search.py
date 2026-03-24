"""Tests for Reciprocal Rank Fusion hybrid search."""

import sqlite3

import pytest

from content_engine.hybrid_search import hybrid_search, reciprocal_rank_fusion


class TestReciprocalRankFusion:
    def test_combines_two_ranked_lists(self):
        list_a = [
            {"id": 1, "content": "A first"},
            {"id": 2, "content": "A second"},
            {"id": 3, "content": "A third"},
        ]
        list_b = [
            {"id": 2, "content": "B first"},
            {"id": 4, "content": "B second"},
            {"id": 1, "content": "B third"},
        ]
        fused = reciprocal_rank_fusion([list_a, list_b])
        # id=2 appears in both lists (rank 2 in A, rank 1 in B) — highest
        # id=1 appears in both lists (rank 1 in A, rank 3 in B)
        ids = [r["id"] for r in fused]
        assert 2 in ids[:2]  # id=2 should be top-ranked
        assert 1 in ids[:2]  # id=1 should also be top-ranked

    def test_handles_empty_list(self):
        fused = reciprocal_rank_fusion([[], []])
        assert fused == []

    def test_handles_single_list(self):
        items = [{"id": 1, "content": "only"}]
        fused = reciprocal_rank_fusion([items])
        assert len(fused) == 1
        assert fused[0]["id"] == 1

    def test_deduplicates_by_id(self):
        list_a = [{"id": 1, "content": "from A"}]
        list_b = [{"id": 1, "content": "from B"}]
        fused = reciprocal_rank_fusion([list_a, list_b])
        assert len(fused) == 1

    def test_respects_limit(self):
        items = [{"id": i, "content": f"item {i}"} for i in range(10)]
        fused = reciprocal_rank_fusion([items], limit=3)
        assert len(fused) == 3

    def test_adds_rrf_score(self):
        items = [{"id": 1, "content": "test"}]
        fused = reciprocal_rank_fusion([items])
        assert "rrf_score" in fused[0]
        assert fused[0]["rrf_score"] > 0


@pytest.fixture
def fts_db(tmp_path):
    """DB with FTS5 and sample data."""
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
            ('fact', 'Ahimsa dairy produces paneer and cheddar', 'Farm Ops', 'dairy'),
            ('fact', 'Sunday Feast serves 50-100 guests weekly', 'Community', 'events');

        CREATE VIRTUAL TABLE web_knowledge_fts USING fts5(
            content, topic, content='web_knowledge', content_rowid='id'
        );
        INSERT INTO web_knowledge_fts(web_knowledge_fts) VALUES('rebuild');
    """)
    conn.commit()
    conn.close()
    return str(db)


class TestHybridSearch:
    def test_returns_results(self, fts_db):
        results = hybrid_search(fts_db, "cows farm")
        assert len(results) >= 1

    def test_results_have_content(self, fts_db):
        results = hybrid_search(fts_db, "dairy paneer")
        assert any("paneer" in r["content"] for r in results)

    def test_pillar_filter(self, fts_db):
        results = hybrid_search(fts_db, "farm", pillar="Cow Life")
        for r in results:
            assert r["pillar"] == "Cow Life"

    def test_empty_query_returns_empty(self, fts_db):
        results = hybrid_search(fts_db, "")
        assert results == []

    def test_respects_limit(self, fts_db):
        results = hybrid_search(fts_db, "farm", limit=1)
        assert len(results) <= 1
