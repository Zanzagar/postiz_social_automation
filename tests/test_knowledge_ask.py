"""Tests for POST /api/knowledge/ask — grounded Q&A over the knowledge base.

The Claude CLI is always mocked (both success and failure paths).
The search path runs against a seeded tmp SQLite DB with a real FTS5
index matching the production migration (b2c3d4e5f6a7).
"""

import sqlite3
import time
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

import api.services.knowledge_ask as knowledge_ask
from api.auth import get_current_user
from api.main import app
from api.routes.knowledge import get_db_path

SOURCE_KEYS = {"content", "fact_type", "topic", "pillar", "site", "page_title", "score"}


@pytest.fixture
def ask_db(tmp_path):
    """Temporary SQLite with knowledge tables, FTS5 index, and sample data."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE web_pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            site TEXT NOT NULL,
            title TEXT,
            body_text TEXT,
            pillar TEXT,
            content_hash TEXT,
            last_crawled DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE web_knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            web_page_id INTEGER REFERENCES web_pages(id),
            fact_type TEXT NOT NULL,
            content TEXT NOT NULL,
            topic TEXT,
            pillar TEXT,
            keywords TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        -- FTS5 index identical to production migration b2c3d4e5f6a7
        CREATE VIRTUAL TABLE web_knowledge_fts USING fts5(
            content, topic,
            content='web_knowledge', content_rowid='id'
        );
        CREATE TRIGGER web_knowledge_ai AFTER INSERT ON web_knowledge BEGIN
            INSERT INTO web_knowledge_fts(rowid, content, topic)
            VALUES (new.id, new.content, new.topic);
        END;

        INSERT INTO web_pages (url, site, title, body_text, pillar, content_hash, last_crawled)
        VALUES ('https://gitavalley.org/cows', 'gitavalley', 'Cow Protection',
                '85 cows on 430 acres.', 'Cow Life', 'abc', '2026-03-01T10:00:00');
        INSERT INTO web_pages (url, site, title, body_text, pillar, content_hash, last_crawled)
        VALUES ('https://gitavalley.org/festivals', 'gitavalley', 'Festivals',
                'Festivals at the farm.', 'Events', 'def', '2026-03-01T09:00:00');

        INSERT INTO web_knowledge (web_page_id, fact_type, content, topic, pillar, keywords)
        VALUES (1, 'program', 'Cow protection program with 85 cows on 430 acres.',
                'Cow Care', 'Cow Life', '["cows","ahimsa"]');
        INSERT INTO web_knowledge (web_page_id, fact_type, content, topic, pillar, keywords)
        VALUES (2, 'event', 'The Festival of Chariots is held every July at Gita Valley.',
                'Festivals', 'Events', '["festival","chariots"]');
        INSERT INTO web_knowledge (web_page_id, fact_type, content, topic, pillar, keywords)
        VALUES (NULL, 'description', 'Ahimsa dairy products include paneer and cheddar.',
                NULL, 'Community', '["dairy"]');
    """)
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def ask_client(ask_db):
    """Override app dependencies for test database and auth."""
    app.dependency_overrides[get_current_user] = lambda: {"sub": "testuser"}
    app.dependency_overrides[get_db_path] = lambda: str(ask_db)
    yield
    app.dependency_overrides.clear()


async def _post_ask(question: str):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post("/api/knowledge/ask", json={"question": question})


@pytest.mark.asyncio
class TestAskSuccess:
    async def test_claude_answer_returned_with_sources(self, ask_client):
        with patch.object(
            knowledge_ask, "_call_claude", return_value="Gita Valley cares for 85 cows."
        ) as mock_cli:
            resp = await _post_ask("How many cows live at the farm?")

        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] == "Gita Valley cares for 85 cows."
        assert data["answered_by"] == "claude"
        assert len(data["sources"]) >= 1
        mock_cli.assert_called_once()

    async def test_source_shape_matches_contract(self, ask_client):
        with patch.object(knowledge_ask, "_call_claude", return_value="An answer."):
            resp = await _post_ask("cows")

        data = resp.json()
        assert data["sources"], "expected at least one source"
        for source in data["sources"]:
            assert set(source.keys()) == SOURCE_KEYS
        cow_source = next(s for s in data["sources"] if "85 cows" in s["content"])
        assert cow_source["fact_type"] == "program"
        assert cow_source["topic"] == "Cow Care"
        assert cow_source["pillar"] == "Cow Life"
        assert cow_source["site"] == "gitavalley"
        assert cow_source["page_title"] == "Cow Protection"
        assert isinstance(cow_source["score"], float)

    async def test_source_without_page_has_null_site(self, ask_client):
        """Entries not linked to a web page (social imports) keep null site/title."""
        with patch.object(knowledge_ask, "_call_claude", return_value="An answer."):
            resp = await _post_ask("ahimsa dairy paneer")

        data = resp.json()
        dairy = next(s for s in data["sources"] if "paneer" in s["content"])
        assert dairy["site"] is None
        assert dairy["page_title"] is None
        assert dairy["topic"] is None

    async def test_prompt_is_grounded_in_snippets_and_question(self, ask_client):
        mock_cli = MagicMock(return_value="Grounded answer.")
        with patch.object(knowledge_ask, "_call_claude", mock_cli):
            resp = await _post_ask("How many cows live at the farm?")

        assert resp.status_code == 200
        prompt = mock_cli.call_args[0][0]
        assert "85 cows" in prompt  # snippet content present
        assert "How many cows live at the farm?" in prompt
        assert "ONLY" in prompt  # grounding instruction
        assert "2-4 warm" in prompt
        assert "Gita Nagari" in prompt  # branding rule mentions the forbidden name
        assert "information is missing" in prompt


@pytest.mark.asyncio
class TestAskDegrade:
    async def test_cli_failure_degrades_to_search_only(self, ask_client):
        with patch.object(knowledge_ask, "_call_claude", side_effect=RuntimeError("CLI exploded")):
            resp = await _post_ask("How many cows live at the farm?")

        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] is None
        assert data["answered_by"] == "search_only"
        assert len(data["sources"]) >= 1  # sources still returned

    async def test_cli_timeout_degrades_to_search_only(self, ask_client, monkeypatch):
        monkeypatch.setattr(knowledge_ask, "CLI_BUDGET_SECONDS", 0.05)

        def slow_cli(prompt):
            time.sleep(0.5)
            return "too late"

        with patch.object(knowledge_ask, "_call_claude", slow_cli):
            resp = await _post_ask("cows")

        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] is None
        assert data["answered_by"] == "search_only"
        assert len(data["sources"]) >= 1

    async def test_empty_cli_answer_degrades(self, ask_client):
        with patch.object(knowledge_ask, "_call_claude", return_value="   \n"):
            resp = await _post_ask("cows")

        data = resp.json()
        assert data["answer"] is None
        assert data["answered_by"] == "search_only"
        assert len(data["sources"]) >= 1


@pytest.mark.asyncio
class TestAskEmpty:
    async def test_no_search_results_returns_empty_and_skips_cli(self, ask_client):
        mock_cli = MagicMock(return_value="should never run")
        with patch.object(knowledge_ask, "_call_claude", mock_cli):
            resp = await _post_ask("zzqx unmatchable gibberish")

        assert resp.status_code == 200
        data = resp.json()
        assert data == {"answer": None, "sources": [], "answered_by": "search_only"}
        mock_cli.assert_not_called()

    async def test_empty_question_returns_empty(self, ask_client):
        mock_cli = MagicMock(return_value="should never run")
        with patch.object(knowledge_ask, "_call_claude", mock_cli):
            resp = await _post_ask("   ")

        assert resp.status_code == 200
        data = resp.json()
        assert data == {"answer": None, "sources": [], "answered_by": "search_only"}
        mock_cli.assert_not_called()

    async def test_missing_question_field_is_422(self, ask_client):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/knowledge/ask", json={})
        assert resp.status_code == 422
