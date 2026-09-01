"""Tool Registry system."""

from typing import Any
from sae.events import Event, EventBus, EventType
from sae.tools.base import BaseTool, ToolResult


class ToolRegistry:
    def __init__(self, event_bus: EventBus):
        self._tools: dict[str, BaseTool] = {}
        self.event_bus = event_bus

    def register_tool(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "version": tool.version,
                "permission_level": tool.permission_level.value,
                "risk_level": tool.risk_level.value,
            }
            for tool in self._tools.values()
        ]

    async def execute_tool(self, tool_name: str, **kwargs: Any) -> ToolResult:
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResult(success=False, error=f"Tool '{tool_name}' not registered in engine.")

        if not tool.validate_input(**kwargs):
            return ToolResult(success=False, error=f"Invalid arguments provided for tool '{tool_name}'.")

        result = await tool.execute(**kwargs)
        return result