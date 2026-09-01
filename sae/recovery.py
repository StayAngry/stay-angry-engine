"""Checkpoint and Recovery Engine for resilient task execution and failure management."""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field
from sae.database import DatabaseManager
from sae.events import Event, EventBus, EventType
from sae.tasks import StepStatus, Task, TaskStatus


class FailureCategory(str, Enum):
    TRANSIENT = "TRANSIENT"
    PERMANENT = "PERMANENT"
    CONFIGURATION = "CONFIGURATION"
    PERMISSION = "PERMISSION"
    RESOURCE = "RESOURCE"
    NETWORK = "NETWORK"
    PROVIDER = "PROVIDER"
    TOOL = "TOOL"
    UNKNOWN = "UNKNOWN"


class RecoveryAction(str, Enum):
    RETRY = "RETRY"
    RESUME = "RESUME"
    PAUSE = "PAUSE"
    REPLAN = "REPLAN"
    FAIL = "FAIL"


class Checkpoint(BaseModel):
    checkpoint_id: str = Field(default_factory=lambda: f"chk_{uuid.uuid4().hex[:8]}")
    task_id: str
    step_index: int
    task_status: TaskStatus
    completed_steps: list[int] = Field(default_factory=list)
    task_payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ArtifactRecord(BaseModel):
    artifact_id: str = Field(default_factory=lambda: f"art_{uuid.uuid4().hex[:8]}")
    task_id: str
    step_id: str
    path: str
    status: str = "VALID"
    size_bytes: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)


class CheckpointManager:
    def __init__(self, db: DatabaseManager, event_bus: EventBus):
        self.db = db
        self.event_bus = event_bus

    async def save_checkpoint(
        self,
        task: Task,
        current_step_index: int,
        completed_step_indices: list[int],
        metadata: dict[str, Any] | None = None
    ) -> Checkpoint:
        chk = Checkpoint(
            task_id=task.id,
            step_index=current_step_index,
            task_status=task.status,
            completed_steps=completed_step_indices,
            task_payload=task.model_dump(),
            metadata=metadata or {}
        )

        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO checkpoints (
                    checkpoint_id, task_id, step_index, task_status,
                    completed_steps, task_payload, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                chk.checkpoint_id,
                chk.task_id,
                chk.step_index,
                chk.task_status.value,
                json.dumps(chk.completed_steps),
                json.dumps(chk.task_payload),
                json.dumps(chk.metadata),
                chk.created_at
            ))
            conn.commit()

        await self.event_bus.emit(
            Event(
                event_type=EventType.CHECKPOINT_SAVED,
                source="CheckpointManager",
                payload={"checkpoint_id": chk.checkpoint_id, "task_id": task.id, "step_index": current_step_index}
            )
        )
        return chk

    def get_latest_checkpoint(self, task_id: str) -> Checkpoint | None:
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM checkpoints WHERE task_id = ? ORDER BY step_index DESC, created_at DESC LIMIT 1",
                (task_id,)
            )
            row = cursor.fetchone()
            if row:
                return Checkpoint(
                    checkpoint_id=row["checkpoint_id"],
                    task_id=row["task_id"],
                    step_index=row["step_index"],
                    task_status=TaskStatus(row["task_status"]),
                    completed_steps=json.loads(row["completed_steps"]),
                    task_payload=json.loads(row["task_payload"]),
                    metadata=json.loads(row["metadata"]),
                    created_at=row["created_at"]
                )
        return None

    def list_interrupted_tasks(self) -> list[str]:
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT task_id FROM checkpoints WHERE task_status IN (?, ?)",
                (TaskStatus.RUNNING.value, TaskStatus.PAUSED.value)
            )
            rows = cursor.fetchall()
            return [r["task_id"] for r in rows]

    def register_artifact(self, artifact: ArtifactRecord) -> None:
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO artifacts (artifact_id, task_id, step_id, path, status, size_bytes, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                artifact.artifact_id,
                artifact.task_id,
                artifact.step_id,
                artifact.path,
                artifact.status,
                artifact.size_bytes,
                artifact.created_at,
                json.dumps(artifact.metadata)
            ))
            conn.commit()

    def get_task_artifacts(self, task_id: str) -> list[ArtifactRecord]:
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM artifacts WHERE task_id = ?", (task_id,))
            rows = cursor.fetchall()
            return [
                ArtifactRecord(
                    artifact_id=r["artifact_id"],
                    task_id=r["task_id"],
                    step_id=r["step_id"],
                    path=r["path"],
                    status=r["status"],
                    size_bytes=r["size_bytes"],
                    created_at=r["created_at"],
                    metadata=json.loads(r["metadata"])
                )
                for r in rows
            ]


class RecoveryEngine:
    def __init__(
        self,
        checkpoint_manager: CheckpointManager,
        db: DatabaseManager,
        event_bus: EventBus,
        max_retries: int = 3,
        backoff_base_seconds: float = 0.2
    ):
        self.checkpoint_manager = checkpoint_manager
        self.db = db
        self.event_bus = event_bus
        self.max_retries = max_retries
        self.backoff_base_seconds = backoff_base_seconds

    def classify_error(self, error_message: str) -> FailureCategory:
        msg = error_message.lower()
        if any(w in msg for w in ["timeout", "timed out", "connection reset", "temporary", "busy"]):
            return FailureCategory.TRANSIENT
        if any(w in msg for w in ["permission denied", "forbidden", "unauthorized"]):
            return FailureCategory.PERMISSION
        if any(w in msg for w in ["disk full", "out of memory", "resource exhausted"]):
            return FailureCategory.RESOURCE
        if any(w in msg for w in ["tool not found", "unregistered tool", "not registered"]):
            return FailureCategory.TOOL
        if any(w in msg for w in ["invalid path", "file not found", "schema error"]):
            return FailureCategory.CONFIGURATION
        return FailureCategory.UNKNOWN

    def determine_action(self, category: FailureCategory, current_attempt: int) -> RecoveryAction:
        if category == FailureCategory.PERMISSION:
            return RecoveryAction.PAUSE
        if category == FailureCategory.TRANSIENT and current_attempt < self.max_retries:
            return RecoveryAction.RETRY
        if category in (FailureCategory.TOOL, FailureCategory.CONFIGURATION):
            return RecoveryAction.REPLAN
        return RecoveryAction.FAIL

    async def record_recovery_event(
        self,
        task_id: str,
        step_index: int,
        category: FailureCategory,
        attempt: int,
        action: RecoveryAction,
        message: str
    ) -> None:
        now_str = datetime.now(timezone.utc).isoformat()
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO recovery_events (task_id, step_index, failure_category, attempt_count, action_taken, message, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (task_id, step_index, category.value, attempt, action.value, message, now_str))
            conn.commit()

        await self.event_bus.emit(
            Event(
                event_type=EventType.GENERIC_LOG,
                source="RecoveryEngine",
                payload={
                    "action": "RECOVERY_EVENT_RECORDED",
                    "task_id": task_id,
                    "recovery_action": action.value,
                    "category": category.value
                }
            )
        )

    async def handle_step_failure(
        self,
        task: Task,
        step_index: int,
        error_message: str,
        attempt: int
    ) -> RecoveryAction:
        category = self.classify_error(error_message)
        action = self.determine_action(category, attempt)

        await self.record_recovery_event(
            task_id=task.id,
            step_index=step_index,
            category=category,
            attempt=attempt,
            action=action,
            message=error_message
        )

        if action == RecoveryAction.RETRY:
            delay = self.backoff_base_seconds * (2 ** (attempt - 1))
            await asyncio.sleep(delay)

        return action