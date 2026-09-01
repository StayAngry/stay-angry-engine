"""Decoupled asynchronous Event Bus and typed event models."""

import asyncio
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine
from pydantic import BaseModel, Field


class EventType(str, Enum):
    STATE_CHANGED = "STATE_CHANGED"
    TASK_STARTED = "TASK_STARTED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    TASK_STATUS_UPDATED = "TASK_STATUS_UPDATED"
    TOOL_EXECUTED = "TOOL_EXECUTED"
    CHECKPOINT_SAVED = "CHECKPOINT_SAVED"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    GENERIC_LOG = "GENERIC_LOG"
    PERMISSION_DENIED = "PERMISSION_DENIED"


class Event(BaseModel):
    event_type: EventType
    source: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EventBus:
    def __init__(self):
        self._subscribers: dict[EventType, list[Callable[[Event], Coroutine[Any, Any, None]]]] = {}

    def subscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event], Coroutine[Any, Any, None]]
    ) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    async def emit(self, event: Event) -> None:
        handlers = self._subscribers.get(event.event_type, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception:
                pass