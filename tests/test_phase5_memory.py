"""Comprehensive Phase 5 test suite validating multi-scope local memory, search, forgetting, and privacy."""

import pytest
from pathlib import Path
from sae.database import DatabaseManager
from sae.events import EventBus
from sae.memory import (
    MemoryConfidence,
    MemoryImportance,
    MemoryManager,
    MemoryScope,
    MemorySource,
    MemoryType,
)


@pytest.fixture
def memory_manager(tmp_path: Path):
    db_file = tmp_path / "test_memory.db"
    db = DatabaseManager(db_file)
    bus = EventBus()
    return MemoryManager(db, bus)


@pytest.mark.asyncio
async def test_remember_and_get(memory_manager: MemoryManager):
    item = await memory_manager.remember(
        content="Prefer manhwa anime reel style",
        memory_type=MemoryType.LONG_TERM,
        scope=MemoryScope.GLOBAL,
        tags=["style", "anime"]
    )
    assert item.memory_id.startswith("mem_")
    
    retrieved = memory_manager.get(item.memory_id)
    assert retrieved is not None
    assert retrieved.content == "Prefer manhwa anime reel style"
    assert retrieved.memory_type == MemoryType.LONG_TERM
    assert "anime" in retrieved.tags


@pytest.mark.asyncio
async def test_search_by_query_and_scope(memory_manager: MemoryManager):
    await memory_manager.remember(
        content="Project A target ratio is 9:16",
        scope=MemoryScope.PROJECT,
        tags=["ratio"]
    )
    await memory_manager.remember(
        content="Project B target ratio is 16:9",
        scope=MemoryScope.PROJECT,
        tags=["ratio"]
    )
    await memory_manager.remember(
        content="Temporary session note",
        scope=MemoryScope.SESSION
    )

    results = memory_manager.search(query="9:16", scope=MemoryScope.PROJECT)
    assert len(results) == 1
    assert "Project A" in results[0].content


@pytest.mark.asyncio
async def test_update_and_conflict_correction(memory_manager: MemoryManager):
    item = await memory_manager.remember(content="Original reel ratio 16:9")
    updated = await memory_manager.update(item.memory_id, "Corrected reel ratio 9:16")
    
    assert updated is not None
    assert updated.content == "Corrected reel ratio 9:16"


@pytest.mark.asyncio
async def test_forget_memory_by_id(memory_manager: MemoryManager):
    item = await memory_manager.remember(content="Delete this note soon")
    deleted = await memory_manager.forget(item.memory_id)
    assert deleted is True
    assert memory_manager.get(item.memory_id) is None


@pytest.mark.asyncio
async def test_clear_session_scope_isolation(memory_manager: MemoryManager):
    await memory_manager.remember(content="Session item 1", scope=MemoryScope.SESSION)
    await memory_manager.remember(content="Session item 2", scope=MemoryScope.SESSION)
    await memory_manager.remember(content="Permanent pref", scope=MemoryScope.GLOBAL)

    cleared_count = await memory_manager.clear_scope(MemoryScope.SESSION)
    assert cleared_count == 2

    # Global memory remains intact
    global_items = memory_manager.search(scope=MemoryScope.GLOBAL)
    assert len(global_items) == 1
    assert global_items[0].content == "Permanent pref"


@pytest.mark.asyncio
async def test_memory_secret_redaction(memory_manager: MemoryManager):
    item = await memory_manager.remember(
        content="User provided api_key=AIzaSySecretToken99 and token_secret_123456"
    )
    assert "AIzaSySecretToken99" not in item.content
    assert "[REDACTED_SECURITY_SENSITIVE_STRING]" in item.content