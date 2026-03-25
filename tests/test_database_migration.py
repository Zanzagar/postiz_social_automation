"""Tests for Alembic migration (Phase 1 — Task #1, subtask 1.4)."""

import os
import tempfile

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command


@pytest.fixture
def alembic_config():
    """Create Alembic config pointing to a temp SQLite database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        cfg = Config("alembic.ini")
        cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
        yield cfg, db_path
    finally:
        os.unlink(db_path)


class TestMigration:
    def test_upgrade_creates_all_tables(self, alembic_config):
        cfg, db_path = alembic_config
        command.upgrade(cfg, "head")

        engine = create_engine(f"sqlite:///{db_path}")
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        expected = {
            "users",
            "content_rows",
            "content_iterations",
            "templates",
            "publish_config",
            "alembic_version",
            # Phase 2
            "web_pages",
            "web_knowledge",
            "social_history",
            "analytics_cache",
            "hashtag_performance",
            # Phase 3
            "media_catalog",
            "media_tags",
            "media_performance",
            "media_adapted",
            "pillars",
            "calendar_plans",
            # Content Intelligence v2
            "brand_settings",
            "few_shot_examples",
            "preference_pairs",
            # FTS5 virtual table + internal tables
            "web_knowledge_fts",
            "web_knowledge_fts_data",
            "web_knowledge_fts_idx",
            "web_knowledge_fts_docsize",
            "web_knowledge_fts_config",
        }
        assert expected == tables

    def test_downgrade_removes_all_tables(self, alembic_config):
        cfg, db_path = alembic_config
        command.upgrade(cfg, "head")
        command.downgrade(cfg, "base")

        engine = create_engine(f"sqlite:///{db_path}")
        inspector = inspect(engine)
        tables = set(inspector.get_table_names()) - {"alembic_version"}
        assert tables == set()

    def test_migration_is_idempotent(self, alembic_config):
        """Running upgrade twice should not error."""
        cfg, _db_path = alembic_config
        command.upgrade(cfg, "head")
        command.upgrade(cfg, "head")  # Should be a no-op

    def test_content_rows_has_correct_fks(self, alembic_config):
        cfg, db_path = alembic_config
        command.upgrade(cfg, "head")

        engine = create_engine(f"sqlite:///{db_path}")
        inspector = inspect(engine)
        fks = inspector.get_foreign_keys("content_rows")
        fk_targets = {(fk["referred_table"], tuple(fk["constrained_columns"])) for fk in fks}
        assert ("templates", ("template_id",)) in fk_targets
        assert ("users", ("created_by",)) in fk_targets

    def test_can_insert_and_query_after_migration(self, alembic_config):
        cfg, db_path = alembic_config
        command.upgrade(cfg, "head")

        engine = create_engine(f"sqlite:///{db_path}")
        with engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO users (username, display_name, password_hash, created_at) "
                    "VALUES ('test', 'Test User', 'hash', datetime('now'))"
                )
            )
            conn.commit()

            result = conn.execute(text("SELECT username FROM users")).fetchone()
            assert result[0] == "test"
