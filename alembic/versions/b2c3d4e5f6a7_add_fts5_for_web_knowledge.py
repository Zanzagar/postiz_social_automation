"""add FTS5 virtual table for web_knowledge search

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-24 13:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create FTS5 virtual table, sync triggers, and populate."""
    conn = op.get_bind()

    # Create FTS5 virtual table (content-linked to web_knowledge)
    conn.execute(
        op.inline_literal(
            "CREATE VIRTUAL TABLE IF NOT EXISTS web_knowledge_fts "
            "USING fts5("
            "content, topic, "
            "content='web_knowledge', content_rowid='id'"
            ")"
        )
    )

    # Sync triggers: INSERT
    conn.execute(
        op.inline_literal("""
            CREATE TRIGGER IF NOT EXISTS web_knowledge_ai
            AFTER INSERT ON web_knowledge BEGIN
                INSERT INTO web_knowledge_fts(rowid, content, topic)
                VALUES (new.id, new.content, new.topic);
            END
        """)
    )

    # Sync triggers: DELETE
    conn.execute(
        op.inline_literal("""
            CREATE TRIGGER IF NOT EXISTS web_knowledge_ad
            AFTER DELETE ON web_knowledge BEGIN
                INSERT INTO web_knowledge_fts(
                    web_knowledge_fts, rowid, content, topic
                )
                VALUES('delete', old.id, old.content, old.topic);
            END
        """)
    )

    # Sync triggers: UPDATE
    conn.execute(
        op.inline_literal("""
            CREATE TRIGGER IF NOT EXISTS web_knowledge_au
            AFTER UPDATE ON web_knowledge BEGIN
                INSERT INTO web_knowledge_fts(
                    web_knowledge_fts, rowid, content, topic
                )
                VALUES('delete', old.id, old.content, old.topic);
                INSERT INTO web_knowledge_fts(rowid, content, topic)
                VALUES (new.id, new.content, new.topic);
            END
        """)
    )

    # Populate from existing rows
    conn.execute(
        op.inline_literal("INSERT INTO web_knowledge_fts(web_knowledge_fts) VALUES('rebuild')")
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(op.inline_literal("DROP TRIGGER IF EXISTS web_knowledge_au"))
    conn.execute(op.inline_literal("DROP TRIGGER IF EXISTS web_knowledge_ad"))
    conn.execute(op.inline_literal("DROP TRIGGER IF EXISTS web_knowledge_ai"))
    conn.execute(op.inline_literal("DROP TABLE IF EXISTS web_knowledge_fts"))
