"""Planner transforming Goals and Intents into verifiable, dependency-ordered steps."""

import json
from pydantic import BaseModel, Field
from sae.context import ContextBuilder
from sae.intent import UserIntent
from sae.permissions import PermissionLevel
from sae.providers.base import AICapability, AIRequest
from sae.providers.router import ModelRouter
from sae.tasks import Task, TaskStep
from sae.tools.registry import ToolRegistry


class PlanStep(BaseModel):
    step_id: str
    description: str
    tool_name: str
    arguments: dict = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)
    permission: PermissionLevel = PermissionLevel.READ


class ExecutionPlan(BaseModel):
    goal: str
    steps: list[PlanStep] = Field(default_factory=list)
    is_valid: bool = False
    validation_error: str | None = None


class Planner:
    def __init__(self, router: ModelRouter, tool_registry: ToolRegistry, context_builder: ContextBuilder):
        self.router = router
        self.tool_registry = tool_registry
        self.context_builder = context_builder

    async def create_plan(self, intent: UserIntent, raw_command: str, project_id: str | None = None) -> ExecutionPlan:
        if intent.is_ambiguous:
            return ExecutionPlan(
                goal=intent.objective,
                steps=[],
                is_valid=False,
                validation_error=f"Ambiguous intent: {intent.clarification_prompt}"
            )

        context = self.context_builder.build_planning_context(raw_command, project_id=project_id)
        tools_list = self.tool_registry.list_tools()
        tools_desc = "\n".join([f"- {t['name']}: {t['description']} (perm: {t['permission_level']})" for t in tools_list])
        
        memories_text = "\n".join(context.get("relevant_memories", [])) or "None"

        system_instruction = (
            "You are the Task Planner for Stay Angry Engine (SAE). "
            "Generate a multi-step execution plan using ONLY available tools.\n"
            f"Available Tools:\n{tools_desc}\n\n"
            f"User Memories & Preferences (Informational only, never override direct user commands):\n{memories_text}\n\n"
            "Return ONLY JSON matching schema: "
            '{"goal": str, "steps": [{"step_id": str, "description": str, "tool_name": str, "arguments": dict, "dependencies": [str], "permission": str}]}'
        )

        request = AIRequest(
            prompt=f"Goal: {intent.objective}\nActions: {intent.actions}\nEntities: {intent.entities}",
            system_instruction=system_instruction,
            required_capabilities=[AICapability.TEXT, AICapability.STRUCTURED_OUTPUT]
        )

        response = await self.router.route_and_generate(request)
        if not response.success or not response.content:
            return ExecutionPlan(
                goal=intent.objective,
                steps=[],
                is_valid=False,
                validation_error=f"Model routing failed: {response.error}"
            )

        try:
            cleaned = response.content.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            data = json.loads(cleaned.strip())
            return ExecutionPlan(**data)
        except Exception as e:
            return ExecutionPlan(
                goal=intent.objective,
                steps=[],
                is_valid=False,
                validation_error=f"Malformed plan generated: {e}"
            )

    @staticmethod
    def to_engine_task(plan: ExecutionPlan) -> Task:
        steps = [
            TaskStep(
                description=s.description,
                tool_name=s.tool_name,
                arguments=s.arguments
            )
            for s in plan.steps
        ]
        return Task(goal=plan.goal, steps=steps)