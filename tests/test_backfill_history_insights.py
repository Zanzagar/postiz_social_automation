"""Tests for the social_history insights backfill script (mocked httpx)."""

import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from content_engine.scripts import backfill_history_insights as script

# Matches the live social_history schema — NO impressions column.
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
"""


def _graph_response(impressions=400, unique=250, metrics=("both",)):
    """Build a mocked httpx response with Graph API insights payload."""
    data = []
    if "both" in metrics or "impressions" in metrics:
        data.append({"name": "post_impressions", "values": [{"value": impressions}]})
    if "both" in metrics or "unique" in metrics:
        data.append({"name": "post_impressions_unique", "values": [{"value": unique}]})
    resp = MagicMock()
    resp.json.return_value = {"data": data}
    resp.raise_for_status.return_value = None
    return resp


def _make_db(tmp_path, monkeypatch, with_impressions=False):
    path = tmp_path / "gvsa.db"
    conn = sqlite3.connect(str(path))
    conn.executescript(SCHEMA)
    if with_impressions:
        conn.execute("ALTER TABLE social_history ADD COLUMN impressions INTEGER DEFAULT 0")
    conn.commit()
    conn.close()
    monkeypatch.setenv("DATABASE_PATH", str(path))
    return str(path)


def _seed(db_path, rows):
    """rows: list of (external_id, reach)."""
    conn = sqlite3.connect(db_path)
    for ext_id, reach in rows:
        conn.execute(
            "INSERT INTO social_history (platform, external_id, post_text, reach)"
            " VALUES ('facebook', ?, 'A post', ?)",
            (ext_id, reach),
        )
    conn.commit()
    conn.close()


def _reach_by_ext(db_path):
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT external_id, reach FROM social_history").fetchall()
    conn.close()
    return dict(rows)


@pytest.fixture
def db(tmp_path, monkeypatch):
    return _make_db(tmp_path, monkeypatch)


class TestSchemaCheck:
    def test_no_impressions_column_in_default_schema(self, db):
        conn = sqlite3.connect(db)
        assert script.has_impressions_column(conn) is False
        conn.close()

    def test_detects_impressions_column(self, tmp_path, monkeypatch):
        path = _make_db(tmp_path, monkeypatch, with_impressions=True)
        conn = sqlite3.connect(path)
        assert script.has_impressions_column(conn) is True
        conn.close()


class TestMain:
    def test_missing_token_exits_with_clear_message_and_no_http(self, db, monkeypatch, caplog):
        monkeypatch.delenv("META_PAGE_ACCESS_TOKEN", raising=False)
        _seed(db, [("fb_1", 0)])
        with patch.object(script.httpx, "get") as mock_get:
            script.main([])
        mock_get.assert_not_called()
        assert "META_PAGE_ACCESS_TOKEN" in caplog.text
        assert _reach_by_ext(db)["fb_1"] == 0

    def test_updates_reach_for_zero_reach_rows_only(self, db, monkeypatch):
        monkeypatch.setenv("META_PAGE_ACCESS_TOKEN", "test-token")
        _seed(db, [("fb_1", 0), ("fb_2", 500)])

        with patch.object(
            script.httpx, "get", return_value=_graph_response(unique=250)
        ) as mock_get:
            script.main([])

        assert mock_get.call_count == 1  # only the reach==0 row
        url = mock_get.call_args[0][0]
        assert url.endswith("/fb_1/insights")
        params = mock_get.call_args[1]["params"]
        assert params["metric"] == "post_impressions,post_impressions_unique"

        result = _reach_by_ext(db)
        assert result["fb_1"] == 250  # post_impressions_unique
        assert result["fb_2"] == 500  # untouched

    def test_token_sent_via_authorization_header_not_query_param(self, db, monkeypatch):
        """Regression (B2): the access token must never travel as a query
        param — httpx exception messages embed the full URL."""
        monkeypatch.setenv("META_PAGE_ACCESS_TOKEN", "test-token")
        _seed(db, [("fb_1", 0)])

        with patch.object(
            script.httpx, "get", return_value=_graph_response(unique=250)
        ) as mock_get:
            script.main([])

        kwargs = mock_get.call_args[1]
        assert kwargs["headers"]["Authorization"] == "Bearer test-token"
        assert "access_token" not in kwargs["params"]
        assert "test-token" not in mock_get.call_args[0][0]  # not in the URL

    def test_token_never_appears_in_logs_on_http_error(self, db, monkeypatch, caplog):
        """Regression (B2): even if an exception message embeds the token
        (httpx puts the full request URL in error text), the logged text
        must have it redacted."""
        token = "sekret-token-123"
        monkeypatch.setenv("META_PAGE_ACCESS_TOKEN", token)
        _seed(db, [("fb_bad", 0)])

        def boom(url, **kwargs):
            raise script.httpx.HTTPError(
                "Client error '400 Bad Request' for url "
                f"'{script.GRAPH_API_BASE}/fb_bad/insights?access_token={token}'"
            )

        with patch.object(script.httpx, "get", side_effect=boom):
            script.main([])  # must not raise

        assert token not in caplog.text
        assert "***" in caplog.text
        assert _reach_by_ext(db)["fb_bad"] == 0  # row skipped

    def test_redact_replaces_token_everywhere(self, monkeypatch):
        script._redact_token = "tok-abc"
        try:
            assert script.redact("x tok-abc y tok-abc") == "x *** y ***"
            assert script.redact("no secret here") == "no secret here"
        finally:
            script._redact_token = ""

    def test_redact_is_noop_without_token(self):
        script._redact_token = ""
        assert script.redact("anything tok-abc") == "anything tok-abc"

    def test_per_post_error_skipped_and_counted(self, db, monkeypatch, caplog):
        monkeypatch.setenv("META_PAGE_ACCESS_TOKEN", "test-token")
        _seed(db, [("fb_bad", 0), ("fb_good", 0)])

        def side_effect(url, **kwargs):
            if "fb_bad" in url:
                raise script.httpx.HTTPError("boom")
            return _graph_response(unique=99)

        with patch.object(script.httpx, "get", side_effect=side_effect):
            script.main([])  # must not raise

        result = _reach_by_ext(db)
        assert result["fb_bad"] == 0  # skipped
        assert result["fb_good"] == 99
        assert "Skipped" in caplog.text or "skipped" in caplog.text

    def test_missing_unique_metric_skips_row(self, db, monkeypatch):
        monkeypatch.setenv("META_PAGE_ACCESS_TOKEN", "test-token")
        _seed(db, [("fb_1", 0)])
        with patch.object(
            script.httpx, "get", return_value=_graph_response(metrics=("impressions",))
        ):
            script.main([])
        assert _reach_by_ext(db)["fb_1"] == 0

    def test_dry_run_writes_nothing(self, db, monkeypatch):
        monkeypatch.setenv("META_PAGE_ACCESS_TOKEN", "test-token")
        _seed(db, [("fb_1", 0)])
        with patch.object(script.httpx, "get", return_value=_graph_response(unique=250)):
            script.main(["--dry-run"])
        assert _reach_by_ext(db)["fb_1"] == 0

    def test_impressions_written_when_column_exists(self, tmp_path, monkeypatch):
        path = _make_db(tmp_path, monkeypatch, with_impressions=True)
        monkeypatch.setenv("META_PAGE_ACCESS_TOKEN", "test-token")
        _seed(path, [("fb_1", 0)])

        with patch.object(
            script.httpx, "get", return_value=_graph_response(impressions=400, unique=250)
        ):
            script.main([])

        conn = sqlite3.connect(path)
        reach, impressions = conn.execute(
            "SELECT reach, impressions FROM social_history WHERE external_id = 'fb_1'"
        ).fetchone()
        conn.close()
        assert reach == 250
        assert impressions == 400

    def test_reach_only_when_no_impressions_column(self, db, monkeypatch):
        monkeypatch.setenv("META_PAGE_ACCESS_TOKEN", "test-token")
        _seed(db, [("fb_1", 0)])

        with patch.object(
            script.httpx, "get", return_value=_graph_response(impressions=400, unique=250)
        ):
            script.main([])  # must not raise despite impressions in the payload

        assert _reach_by_ext(db)["fb_1"] == 250
