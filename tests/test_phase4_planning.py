"""Comprehensive Phase 4 test suite validating intent, planning, repair, and zero-trust execution."""

import pytest
from pathlib import Path
from sae.context import ContextBuilder
from sae.events import EventBus
from sae.executor import ExecutionEngine
from sae.intent import IntentAnalyzer, UserIntent
from sae.permissions import PermissionLevel
from sae.planning import ExecutionPlan, PlanStep, Planner
from sae.providers.manager import ProviderManager
from sae.providers.mock import MockProvider
from sae.providers.router import ModelRouter
from sae.tasks import TaskStatus
from sae.tools.filesystem import CreateDirectoryTool, DeletePathTool, ReadFileTool, WriteFileTool
from sae.tools.registry import ToolRegistry
from sae.validator import PlanValidator
from sae.workspace import WorkspaceSandbox


@pytest.fixture
def test_runtime(tmp_path: Path):
    bus = EventBus()
    sandbox = WorkspaceSandbox(tmp_path)
    registry = ToolRegistry(bus)
    
    registry.register_tool(CreateDirectoryTool(sandbox))
    registry.register_tool(WriteFileTool(sandbox))
    registry.register_tool(ReadFileTool(sandbox))
    registry.register_tool(DeletePathTool(sandbox))

    manager = ProviderManager(bus)
    mock = MockProvider()
    manager.register_provider(mock)

    router = ModelRouter(manager, bus, priority=["mock"])
    context_builder = ContextBuilder(registry)
    validator = PlanValidator(registry)
    executor = ExecutionEngine(registry, bus)

    return sandbox, registry, router, context_builder, validator, executor


@pytest.mark.asyncio
async def test_ambiguous_intent_detection(test_runtime):
    _, _, router, _, _, _ = test_runtime
    analyzer = IntentAnalyzer(router)
    
    intent = await analyzer.analyze("")
    assert intent.is_ambiguous is True
    assert intent.clarification_prompt is not None


def test_plan_validator_catches_unregistered_tool(test_runtime):
    _, _, _, _, validator, _ = test_runtime
    
    bad_plan = ExecutionPlan(
        goal="Unsafe execution",
        steps=[
            PlanStep(
                step_id="001",
                description="Run shell",
                tool_name="unregistered_shell_tool",
                arguments={"cmd": "calc.exe"}
            )
        ]
    )

    is_valid, err = validator.validate_plan(bad_plan)
    assert is_valid is False
    assert "unregistered tool" in err


def test_plan_validator_catches_invalid_arguments(test_runtime):
    _, _, _, _, validator, _ = test_runtime
    
    bad_plan = ExecutionPlan(
        goal="Invalid args",
        steps=[
            PlanStep(
                step_id="001",
                description="Make folder",
                tool_name="fs_create_directory",
                arguments={}  # Missing required 'path'
            )
        ]
    )

    is_valid, err = validator.validate_plan(bad_plan)
    assert is_valid is False
    assert "invalid arguments" in err


def test_plan_repair_fixes_common_tool_naming(test_runtime):
    _, _, _, _, validator, _ = test_runtime
    
    misnamed_plan = ExecutionPlan(
        goal="Fix tool names",
        steps=[
            PlanStep(
                step_id="001",
                description="Make folder",
                tool_name="make_folder",
                arguments={"path": "AnimeFolder"}
            )
        ]
    )

    repaired = validator.attempt_repair(misnamed_plan)
    assert repaired.is_valid is True
    assert repaired.steps[0].tool_name == "fs_create_directory"


@pytest.mark.asyncio
async def test_full_plan_to_execution_pipeline(test_runtime, tmp_path: Path):
    sandbox, registry, router, context_builder, validator, executor = test_runtime
    
    plan = ExecutionPlan(
        goal="Create anime project workspace",
        steps=[
            PlanStep(
                step_id="001",
                description="Create folder",
                tool_name="fs_create_directory",
                arguments={"path": "AnimeProject"}
            ),
            PlanStep(
                step_id="002",
                description="Create note file",
                tool_name="fs_write_file",
                arguments={"path": "AnimeProject/notes.txt", "content": "Scene 1 Setup"},
                dependencies=["001"]
            )
        ]
    )

    is_valid, _ = validator.validate_plan(plan)
    assert is_valid is True

    task = Planner.to_engine_task(plan)
    result_task = await executor.execute_task(task)

    assert result_task.status == TaskStatus.COMPLETED
    assert (tmp_path / "AnimeProject" / "notes.txt").exists()
    assert (tmp_path / "AnimeProject" / "notes.txt").read_text(encoding="utf-8") == "Scene 1 Setup"