"""Task Execution Engine executing discrete task steps with checkpointing and recovery."""

import time
from pathlib import Path
from typing import Any
from sae.events import Event, EventBus, EventType
from sae.recovery import ArtifactRecord, CheckpointManager, RecoveryAction, RecoveryEngine
from sae.tasks import StepStatus, Task, TaskStatus, TaskStep
from sae.tools.registry import ToolRegistry


class ExecutionEngine:
    def __init__(
        self,
        tool_registry: ToolRegistry,
        event_bus: EventBus,
        checkpoint_manager: CheckpointManager | None = None,
        recovery_engine: RecoveryEngine | None = None
    ):
        self.tool_registry = tool_registry
        self.event_bus = event_bus
        self.checkpoint_manager = checkpoint_manager
        self.recovery_engine = recovery_engine

    async def execute_task(self, task: Task) -> Task:
        task.status = TaskStatus.RUNNING
        completed_indices: list[int] = []

        await self.event_bus.emit(
            Event(
                event_type=EventType.TASK_STARTED,
                source="ExecutionEngine",
                payload={"task_id": task.id, "goal": task.goal, "total_steps": len(task.steps)}
            )
        )

        for idx, step in enumerate(task.steps):
            if step.status == StepStatus.COMPLETED:
                completed_indices.append(idx)
                continue

            step_success = False
            attempt = 1
            max_attempts = 3 if self.recovery_engine else 1

            while attempt <= max_attempts and not step_success:
                step.status = StepStatus.RUNNING
                tool = self.tool_registry.get_tool(step.tool_name)
                
                if not tool:
                    step.status = StepStatus.FAILED
                    step.error = f"Tool '{step.tool_name}' is not registered."
                    break

                try:
                    result = await tool.execute(**step.arguments)
                    step.result = result
                    step.status = StepStatus.COMPLETED
                    step_success = True
                    completed_indices.append(idx)

                    # Track artifacts if file was written
                    if step.tool_name == "fs_write_file" and self.checkpoint_manager:
                        path_arg = step.arguments.get("path", "")
                        self.checkpoint_manager.register_artifact(
                            ArtifactRecord(
                                task_id=task.id,
                                step_id=str(idx),
                                path=path_arg,
                                size_bytes=len(step.arguments.get("content", ""))
                            )
                        )

                    # Save verified checkpoint after step success
                    if self.checkpoint_manager:
                        await self.checkpoint_manager.save_checkpoint(
                            task=task,
                            current_step_index=idx,
                            completed_step_indices=completed_indices
                        )

                except Exception as e:
                    step.error = str(e)
                    step.status = StepStatus.FAILED

                    if self.recovery_engine:
                        action = await self.recovery_engine.handle_step_failure(
                            task=task,
                            step_index=idx,
                            error_message=str(e),
                            attempt=attempt
                        )
                        if action == RecoveryAction.RETRY:
                            attempt += 1
                            continue
                        elif action == RecoveryAction.PAUSE:
                            task.status = TaskStatus.PAUSED
                            return task
                    break

            if not step_success:
                task.status = TaskStatus.FAILED
                await self.event_bus.emit(
                    Event(
                        event_type=EventType.TASK_FAILED,
                        source="ExecutionEngine",
                        payload={"task_id": task.id, "failed_step_index": idx, "error": step.error}
                    )
                )
                return task

        task.status = TaskStatus.COMPLETED
        await self.event_bus.emit(
            Event(
                event_type=EventType.TASK_COMPLETED,
                source="ExecutionEngine",
                payload={"task_id": task.id, "goal": task.goal}
            )
        )
        return task