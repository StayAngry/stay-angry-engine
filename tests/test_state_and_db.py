import pytest
from pathlib import Path
from sae.database import DatabaseManager
from sae.events import Event, EventBus, EventType
from sae.state import EngineStatus, StateManager


def test_database_initialization_and_kv_store(tmp_path: Path):
    db_file = tmp_path / "test_state.db"
    db = DatabaseManager(db_file)
    db.set_state("active_project", {"id": "proj_123", "name": "Test Project"})
    retrieved = db.get_state("active_project")
    assert retrieved is not None
    assert retrieved["id"] == "proj_123"


@pytest.mark.asyncio
async def test_state_manager_status_update(tmp_path: Path):
    db_file = tmp_path / "test_state.db"
    db = DatabaseManager(db_file)
    bus = EventBus()
    
    state_events = []
    async def capture_event(event: Event):
        state_events.append(event)
        
    bus.subscribe(EventType.STATE_CHANGED, capture_event)
    
    manager = StateManager(db, bus)
    await manager.update_status(EngineStatus.READY, "Subsystems online")
    
    status_info = manager.get_current_status()
    assert status_info["status"] == EngineStatus.READY.value
    assert len(state_events) == 1