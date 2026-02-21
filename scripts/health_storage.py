"""SQLite storage layer for health check results and state transitions."""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

DEFAULT_DB_PATH = Path(os.getenv("HEALTH_DB_PATH", "var/health.sqlite"))


class HealthStorage:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS health_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    response_time_ms INTEGER,
                    details TEXT,
                    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_health_service_time
                    ON health_checks(service_name, checked_at);

                CREATE TABLE IF NOT EXISTS state_transitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_name TEXT NOT NULL,
                    from_status TEXT NOT NULL,
                    to_status TEXT NOT NULL,
                    webhook_sent BOOLEAN DEFAULT FALSE,
                    transitioned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_transitions_service
                    ON state_transitions(service_name, transitioned_at);
                """
            )

    def record_check(
        self,
        service_name: str,
        status: str,
        response_time_ms: Optional[int] = None,
        details: Optional[dict] = None,
    ) -> int:
        """Record a health check result. Returns the row ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """INSERT INTO health_checks
                   (service_name, status, response_time_ms, details)
                   VALUES (?, ?, ?, ?)""",
                (
                    service_name,
                    status,
                    response_time_ms,
                    json.dumps(details) if details else None,
                ),
            )
            return cursor.lastrowid

    def get_last_status(self, service_name: str) -> Optional[str]:
        """Get the most recent status for a service."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """SELECT status FROM health_checks
                   WHERE service_name = ?
                   ORDER BY checked_at DESC LIMIT 1""",
                (service_name,),
            ).fetchone()
            return row[0] if row else None

    def record_transition(
        self, service_name: str, from_status: str, to_status: str
    ) -> int:
        """Record a state transition. Returns the row ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """INSERT INTO state_transitions
                   (service_name, from_status, to_status)
                   VALUES (?, ?, ?)""",
                (service_name, from_status, to_status),
            )
            return cursor.lastrowid

    def mark_webhook_sent(self, transition_id: int):
        """Mark a transition's webhook as sent."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE state_transitions SET webhook_sent = TRUE WHERE id = ?",
                (transition_id,),
            )

    def get_history(
        self, hours: int = 24, service_name: Optional[str] = None
    ) -> list[dict]:
        """Get health check history for the last N hours."""
        query = """SELECT service_name, status, response_time_ms,
                          details, checked_at
                   FROM health_checks
                   WHERE checked_at >= datetime('now', ?)"""
        params: list = [f"-{hours} hours"]
        if service_name:
            query += " AND service_name = ?"
            params.append(service_name)
        query += " ORDER BY checked_at DESC"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            return [dict(row) for row in conn.execute(query, params)]

    def get_uptime_stats(self, days: int = 7) -> dict[str, float]:
        """Calculate uptime percentage per service over N days."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT service_name,
                       SUM(CASE WHEN status = 'healthy' THEN 1 ELSE 0 END) as healthy,
                       COUNT(*) as total
                FROM health_checks
                WHERE checked_at >= datetime('now', ?)
                GROUP BY service_name
                """,
                (f"-{days} days",),
            ).fetchall()
            return {
                row[0]: (row[1] / row[2] * 100) if row[2] > 0 else 0.0
                for row in rows
            }
