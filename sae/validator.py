"""Plan Validator enforcing tool schemas, dependency graphs, and security boundaries."""

from sae.planning import ExecutionPlan
from sae.tools.registry import ToolRegistry


class PlanValidator:
    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry

    def validate_plan(self, plan: ExecutionPlan) -> tuple[bool, str | None]:
        if not plan.steps:
            return False, "Plan contains zero executable steps."

        step_ids = set()
        for step in plan.steps:
            if step.step_id in step_ids:
                return False, f"Duplicate step ID '{step.step_id}' found in plan."
            step_ids.add(step.step_id)

            # Tool existence check
            tool = self.tool_registry.get_tool(step.tool_name)
            if not tool:
                return False, f"Step '{step.step_id}' uses unregistered tool: '{step.tool_name}'."

            # Tool argument structure check
            if not tool.validate_input(**step.arguments):
                return False, f"Step '{step.step_id}' provided invalid arguments for tool '{step.tool_name}'."

            # Dependency verification
            for dep in step.dependencies:
                if dep not in step_ids or dep == step.step_id:
                    return False, f"Step '{step.step_id}' references invalid dependency '{dep}'."

        return True, None

    def attempt_repair(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Attempts safe repair of minor tool name discrepancies."""
        for step in plan.steps:
            if not self.tool_registry.get_tool(step.tool_name):
                # Common mapping repair
                if "make_folder" in step.tool_name or "mkdir" in step.tool_name:
                    step.tool_name = "fs_create_directory"
                elif "write" in step.tool_name or "create_file" in step.tool_name:
                    step.tool_name = "fs_write_file"
                elif "read" in step.tool_name:
                    step.tool_name = "fs_read_file"
                elif "delete" in step.tool_name or "rm" in step.tool_name:
                    step.tool_name = "fs_delete_path"

        is_valid, err = self.validate_plan(plan)
        plan.is_valid = is_valid
        plan.validation_error = err
        return plan