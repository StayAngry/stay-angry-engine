import pytest
from pathlib import Path
from sae.events import EventBus
from sae.executor import ExecutionEngine
from sae.tasks import Task, TaskStatus, TaskStep
from sae.tools.filesystem import CreateDirectoryTool, WriteFileTool, ReadFileTool, DeletePathTool
from sae.tools.registry import ToolRegistry
from sae.workspace import WorkspaceSandbox


@pytest.mark.asyncio
async def test_full_task_execution_pipeline(tmp_path: Path):
    sandbox = WorkspaceSandbox(tmp_path)
    bus = EventBus()
    registry = ToolRegistry(bus)

    registry.register_tool(CreateDirectoryTool(sandbox))
    registry.register_tool(WriteFileTool(sandbox))
    registry.register_tool(ReadFileTool(sandbox))
    registry.register_tool(DeletePathTool(sandbox))

    executor = ExecutionEngine(registry, bus)

    task = Task(
        goal="Create AnimeReel project folder and config file",
        steps=[
            TaskStep(
                description="Create folder",
                tool_name="fs_create_directory",
                arguments={"path": "AnimeReel"}
            ),
            TaskStep(
                description="Create file",
                tool_name="fs_write_file",
                arguments={"path": "AnimeReel/project.json", "content": '{"title": "Anime Reel"}'}
            ),
            TaskStep(
                description="Read file",
                tool_name="fs_read_file",
                arguments={"path": "AnimeReel/project.json"}
            )
        ]
    )

    result_task = await executor.execute_task(task)

    assert result_task.status == TaskStatus.COMPLETED
    assert len(result_task.steps) == 3
    assert result_task.steps[0].status == TaskStatus.COMPLETED
    assert result_task.steps[1].status == TaskStatus.COMPLETED
    assert result_task.steps[2].status == TaskStatus.COMPLETED
    assert (tmp_path / "AnimeReel" / "project.json").exists()