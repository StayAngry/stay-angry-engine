"""Comprehensive Phase 6 test suite validating checkpoint persistence, bounded retries, and failure recovery."""

import pytest
from pathlib import Path
from sae.database import DatabaseManager
from sae.events import EventBus
from sae.executor import ExecutionEngine
from sae.recovery import (
    ArtifactRecord,
    CheckpointManager,
    FailureCategory,
    RecoveryAction,
    RecoveryEngine,
)
from sae.tasks import StepStatus, Task, TaskStatus, TaskStep
from sae.tools.filesystem import CreateDirectoryTool, WriteFileTool
from sae.tools.registry import ToolRegistry
from sae.workspace import WorkspaceSandbox


@pytest.fixture
def recovery_runtime(tmp_path: Path):
    db_file = tmp_path / "test_recovery.db"
    db = DatabaseManager(db_file)
    bus = EventBus()
    chk_manager = CheckpointManager(db, bus)
    rec_engine = RecoveryEngine(chk_manager, db, bus, max_retries=2, backoff_base_seconds=0.01)
    sandbox = WorkspaceSandbox(tmp_path)
    registry = ToolRegistry(bus)
    registry.register_tool(CreateDirectoryTool(sandbox))
    registry.register_tool(WriteFileTool(sandbox))

    return db, bus, chk_manager, rec_engine, sandbox, registry


@pytest.mark.asyncio
async def test_checkpoint_persistence(recovery_runtime):
    _, _, chk_manager, _, _, _ = recovery_runtime
    
    task = Task(goal="Test persistent checkpointing", steps=[
        TaskStep(description="Step 1", tool_name="fs_create_directory", arguments={"path": "dir1"})
    ])
    
    chk = await chk_manager.save_checkpoint(task, current_step_index=0, completed_step_indices=[0])
    assert chk.checkpoint_id.startswith("chk_")

    loaded = chk_manager.get_latest_checkpoint(task.id)
    assert loaded is not None
    assert loaded.step_index == 0
    assert loaded.task_id == task.id


def test_failure_classification(recovery_runtime):
    _, _, _, rec_engine, _, _ = recovery_runtime

    assert rec_engine.classify_error("Operation timed out") == FailureCategory.TRANSIENT
    assert rec_engine.classify_error("Permission denied on workspace") == FailureCategory.PERMISSION
    assert rec_engine.classify_error("Tool 'fake_tool' not registered") == FailureCategory.TOOL


@pytest.mark.asyncio
async def test_artifact_tracking_during_execution(recovery_runtime, tmp_path: Path):
    _, bus, chk_manager, rec_engine, _, registry = recovery_runtime
    executor = ExecutionEngine(registry, bus, chk_manager, rec_engine)

    task = Task(
        goal="Generate artifact file",
        steps=[
            TaskStep(
                description="Write video config",
                tool_name="fs_write_file",
                arguments={"path": "video_config.json", "content": "{\"fps\": 60}"}
            )
        ]
    )

    completed = await executor.execute_task(task)
    assert completed.status == TaskStatus.COMPLETED

    artifacts = chk_manager.get_task_artifacts(task.id)
    assert len(artifacts) == 1
    assert artifacts[0].path == "video_config.json"
    assert (tmp_path / "video_config.json").exists()


@pytest.mark.asyncio
async def test_resuming_from_completed_step(recovery_runtime, tmp_path: Path):
    _, bus, chk_manager, rec_engine, _, registry = recovery_runtime
    executor = ExecutionEngine(registry, bus, chk_manager, rec_engine)

    step1 = TaskStep(
        description="Create folder",
        tool_name="fs_create_directory",
        arguments={"path": "output_folder"},
        status=StepStatus.COMPLETED  # Already completed in prior run
    )
    step2 = TaskStep(
        description="Create file",
        tool_name="fs_write_file",
        arguments={"path": "output_folder/scene.txt", "content": "Scene 1"}
    )

    task = Task(goal="Resume task", steps=[step1, step2])
    completed = await executor.execute_task(task)

    assert completed.status == TaskStatus.COMPLETED
    assert (tmp_path / "output_folder" / "scene.txt").exists()