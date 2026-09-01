"""Memory subsystem supporting Short-Term, Working, and Long-Term local persistence."""

import json
import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field
from sae.database import DatabaseManager
from sae.events import Event, EventBus, EventType


class MemoryType(str, Enum):
    SHORT_TERM = "SHORT_TERM"
    WORKING = "WORKING"
    LONG_TERM = "LONG_TERM"


class MemoryScope(str, Enum):
    SESSION = "SESSION"
    TASK = "TASK"
    PROJECT = "PROJECT"
    GLOBAL = "GLOBAL"


class MemoryImportance(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class MemoryConfidence(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class MemorySource(str, Enum):
    EXPLICIT_USER = "EXPLICIT_USER"
    TASK_RESULT = "TASK_RESULT"
    SYSTEM = "SYSTEM"
    TOOL_RESULT = "TOOL_RESULT"
    AI_INFERENCE = "AI_INFERENCE"


class MemoryItem(BaseModel):
    memory_id: str = Field(default_factory=lambda: f"mem_{uuid.uuid4().hex[:8]}")
    memory_type: MemoryType = MemoryType.SHORT_TERM
    scope: MemoryScope = MemoryScope.SESSION
    content: str
    source: MemorySource = MemorySource.EXPLICIT_USER
    importance: MemoryImportance = MemoryImportance.NORMAL
    confidence: MemoryConfidence = MemoryConfidence.HIGH
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MemoryManager:
    # Secret pattern regexes for safe offline redaction
    PATTERNS = [
        re.compile(r"(api[_-]?key|secret|token|password)[\s:=]+([A-Za-z0-9_\-]{8,})", re.IGNORECASE),
        re.compile(r"AIzaSy[A-Za-z0-9_\-]{33}")
    ]

    def __init__(self, db: DatabaseManager, event_bus: EventBus):
        self.db = db
        self.event_bus = event_bus

    def _sanitize(self, text: str) -> str:
        sanitized = text
        for pattern in self.PATTERNS:
            sanitized = pattern.sub("[REDACTED_SECURITY_SENSITIVE_STRING]", sanitized)
        return sanitized

    async def remember(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.SHORT_TERM,
        scope: MemoryScope = MemoryScope.SESSION,
        source: MemorySource = MemorySource.EXPLICIT_USER,
        importance: MemoryImportance = MemoryImportance.NORMAL,
        confidence: MemoryConfidence = MemoryConfidence.HIGH,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None
    ) -> MemoryItem:
        sanitized_content = self._sanitize(content)

        item = MemoryItem(
            memory_type=memory_type,
            scope=scope,
            content=sanitized_content,
            source=source,
            importance=importance,
            confidence=confidence,
            tags=tags or [],
            metadata=metadata or {}
        )

        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO memories (
                    memory_id, memory_type, scope, content, source,
                    importance, confidence, tags, metadata, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.memory_id,
                item.memory_type.value,
                item.scope.value,
                item.content,
                item.source.value,
                item.importance.value,
                item.confidence.value,
                json.dumps(item.tags),
                json.dumps(item.metadata),
                item.created_at,
                item.updated_at
            ))
            conn.commit()

        await self.event_bus.emit(
            Event(
                event_type=EventType.GENERIC_LOG,
                source="MemoryManager",
                payload={"action": "MEMORY_CREATED", "memory_id": item.memory_id, "scope": item.scope.value}
            )
        )
        return item

    def get(self, memory_id: str) -> MemoryItem | None:
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM memories WHERE memory_id = ?", (memory_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_item(row)
        return None

    def search(
        self,
        query: str = "",
        scope: MemoryScope | None = None,
        memory_type: MemoryType | None = None,
        tag: str | None = None,
        limit: int = 10
    ) -> list[MemoryItem]:
        query_sql = "SELECT * FROM memories WHERE 1=1"
        params: list[Any] = []

        if query.strip():
            query_sql += " AND content LIKE ?"
            params.append(f"%{query.strip()}%")

        if scope:
            query_sql += " AND scope = ?"
            params.append(scope.value)

        if memory_type:
            query_sql += " AND memory_type = ?"
            params.append(memory_type.value)

        if tag:
            query_sql += " AND tags LIKE ?"
            params.append(f"%{tag}%")

        query_sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query_sql, tuple(params))
            rows = cursor.fetchall()
            return [self._row_to_item(r) for r in rows]

    async def update(self, memory_id: str, new_content: str) -> MemoryItem | None:
        item = self.get(memory_id)
        if not item:
            return None

        sanitized = self._sanitize(new_content)
        now_str = datetime.now(timezone.utc).isoformat()
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE memories
                SET content = ?, updated_at = ?
                WHERE memory_id = ?
            """, (sanitized, now_str, memory_id))
            conn.commit()

        await self.event_bus.emit(
            Event(
                event_type=EventType.GENERIC_LOG,
                source="MemoryManager",
                payload={"action": "MEMORY_UPDATED", "memory_id": memory_id}
            )
        )
        return self.get(memory_id)

    async def forget(self, memory_id: str) -> bool:
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories WHERE memory_id = ?", (memory_id,))
            deleted = cursor.rowcount > 0
            conn.commit()

        if deleted:
            await self.event_bus.emit(
                Event(
                    event_type=EventType.GENERIC_LOG,
                    source="MemoryManager",
                    payload={"action": "MEMORY_FORGOTTEN", "memory_id": memory_id}
                )
            )
        return deleted

    async def clear_scope(self, scope: MemoryScope) -> int:
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories WHERE scope = ?", (scope.value,))
            count = cursor.rowcount
            conn.commit()

        await self.event_bus.emit(
            Event(
                event_type=EventType.GENERIC_LOG,
                source="MemoryManager",
                payload={"action": "SCOPE_CLEARED", "scope": scope.value, "count": count}
            )
        )
        return count

    def _row_to_item(self, row: sqlite3.Row) -> MemoryItem:
        return MemoryItem(
            memory_id=row["memory_id"],
            memory_type=MemoryType(row["memory_type"]),
            scope=MemoryScope(row["scope"]),
            content=row["content"],
            source=MemorySource(row["source"]),
            importance=MemoryImportance(row["importance"]),
            confidence=MemoryConfidence(row["confidence"]),
            tags=json.loads(row["tags"]),
            metadata=json.loads(row["metadata"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )