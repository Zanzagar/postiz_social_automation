"""Tests for health_storage.py - SQLite storage layer."""


class TestHealthStorageSchema:
    def test_schema_creation(self, temp_db):
        """Schema tables should exist after initialization."""
        import sqlite3

        with sqlite3.connect(temp_db.db_path) as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            table_names = [t[0] for t in tables]
        assert "health_checks" in table_names
        assert "state_transitions" in table_names

    def test_schema_creation_idempotent(self, temp_db):
        """Re-initializing schema should not fail."""
        temp_db._init_schema()
        temp_db._init_schema()


class TestRecordCheck:
    def test_record_check_returns_row_id(self, temp_db):
        row_id = temp_db.record_check("postiz", "healthy", 50, {"docker_health": "healthy"})
        assert isinstance(row_id, int)
        assert row_id > 0

    def test_record_check_without_optional_fields(self, temp_db):
        row_id = temp_db.record_check("postiz", "unhealthy")
        assert row_id > 0


class TestGetLastStatus:
    def test_returns_most_recent_status(self, temp_db):
        temp_db.record_check("postiz", "healthy", 50)
        temp_db.record_check("postiz", "unhealthy", 100)
        status = temp_db.get_last_status("postiz")
        assert status == "unhealthy"

    def test_returns_none_for_unknown_service(self, temp_db):
        status = temp_db.get_last_status("nonexistent")
        assert status is None


class TestStateTransitions:
    def test_record_transition_returns_row_id(self, temp_db):
        tid = temp_db.record_transition("postiz", "healthy", "unhealthy")
        assert isinstance(tid, int)
        assert tid > 0

    def test_mark_webhook_sent(self, temp_db):
        import sqlite3

        tid = temp_db.record_transition("postiz", "healthy", "unhealthy")
        temp_db.mark_webhook_sent(tid)

        with sqlite3.connect(temp_db.db_path) as conn:
            row = conn.execute(
                "SELECT webhook_sent FROM state_transitions WHERE id = ?", (tid,)
            ).fetchone()
        assert row[0] == 1


class TestHistory:
    def test_returns_all_recent_checks(self, temp_db):
        temp_db.record_check("postiz", "healthy", 50)
        temp_db.record_check("redis", "unhealthy", 100)
        history = temp_db.get_history(hours=1)
        assert len(history) == 2

    def test_filter_by_service_name(self, temp_db):
        temp_db.record_check("postiz", "healthy", 50)
        temp_db.record_check("redis", "unhealthy", 100)
        history = temp_db.get_history(hours=1, service_name="postiz")
        assert len(history) == 1
        assert history[0]["service_name"] == "postiz"


class TestUptimeStats:
    def test_uptime_calculation(self, temp_db):
        for _ in range(3):
            temp_db.record_check("postiz", "healthy", 50)
        temp_db.record_check("postiz", "unhealthy", 50)
        stats = temp_db.get_uptime_stats(days=1)
        assert abs(stats["postiz"] - 75.0) < 0.01

    def test_empty_returns_empty_dict(self, temp_db):
        stats = temp_db.get_uptime_stats(days=1)
        assert stats == {}
