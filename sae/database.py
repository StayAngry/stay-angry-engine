"""SQLite persistence manager for audit logs, checkpoints, engine state, memories, and artifacts."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from sae.events import Event


class DatabaseManager:
    def __init__(self, db_path: Path):
        self.db_path = db_path.resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    action TEXT,
                    status TEXT,
                    details TEXT
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS engine_state (
                    state_key TEXT PRIMARY KEY,
                    state_value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    memory_id TEXT PRIMARY KEY,
                    memory_type TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    importance TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    step_index INTEGER NOT NULL,
                    task_status TEXT NOT NULL,
                    completed_steps TEXT NOT NULL,
                    task_payload TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    metadata TEXT NOT NULL
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recovery_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    step_index INTEGER NOT NULL,
                    failure_category TEXT NOT NULL,
                    attempt_count INTEGER NOT NULL,
                    action_taken TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_scope ON memories(scope);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_checkpoints_task ON checkpoints(task_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_task ON artifacts(task_id);")
            conn.commit()

    def log_audit_event(self, event: Event) -> None:
        action = event.payload.get("action", event.event_type.value)
        status = event.payload.get("status", "INFO")
        details = json.dumps(event.payload)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_logs (timestamp, event_type, source, action, status, details)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                event.timestamp.isoformat(),
                event.event_type.value,
                event.source,
                action,
                status,
                details
            ))
            conn.commit()

    def set_state(self, key: str, value: Any) -> None:
        serialized = json.dumps(value)
        now_str = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO engine_state (state_key, state_value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(state_key) DO UPDATE SET
                    state_value = excluded.state_value,
                    updated_at = excluded.updated_at
            """, (key, serialized, now_str))
            conn.commit()

    def get_state(self, key: str, default: Any = None) -> Any:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT state_value FROM engine_state WHERE state_key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return json.loads(row["state_value"])
            return default

    def get_recent_audit_logs(self, limit: int = 10) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]