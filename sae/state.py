"""High-level state manager for engine lifecycle and execution tracking."""

from enum import Enum
from typing import Any
from sae.database import DatabaseManager
from sae.events import Event, EventBus, EventType


class EngineStatus(str, Enum):
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    BUSY = "BUSY"
    DEGRADED = "DEGRADED"
    STOPPED = "STOPPED"


class StateManager:
    def __init__(self, db: DatabaseManager, event_bus: EventBus):
        self.db = db
        self.event_bus = event_bus

    async def update_status(self, new_status: EngineStatus, reason: str = "") -> None:
        self.db.set_state("engine_status", new_status.value)
        self.db.set_state("engine_status_reason", reason)
        
        await self.event_bus.emit(
            Event(
                event_type=EventType.STATE_CHANGED,
                source="StateManager",
                payload={"status": new_status.value, "reason": reason}
            )
        )

    def get_current_status(self) -> dict[str, Any]:
        status = self.db.get_state("engine_status", EngineStatus.STOPPED.value)
        reason = self.db.get_state("engine_status_reason", "Engine offline.")
        return {"status": status, "reason": reason}