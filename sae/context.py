"""Context Builder providing scoped, privacy-safe runtime context with memory integration."""

from typing import Any
from sae.config import settings
from sae.memory import MemoryManager
from sae.providers.resources import ResourceAuditor
from sae.tools.registry import ToolRegistry


class ContextBuilder:
    def __init__(self, tool_registry: ToolRegistry, memory_manager: MemoryManager | None = None):
        self.tool_registry = tool_registry
        self.memory_manager = memory_manager

    def build_planning_context(self, user_command: str, max_memories: int = 5) -> dict[str, Any]:
        tools_summary = self.tool_registry.list_tools()
        resources = ResourceAuditor.get_local_resource_metrics(str(settings.workspace_root))
        
        relevant_memories = []
        if self.memory_manager:
            # Query relevant memories based on user command keywords
            keywords = [w for w in user_command.split() if len(w) > 3]
            query_str = keywords[0] if keywords else ""
            items = self.memory_manager.search(query=query_str, limit=max_memories)
            relevant_memories = [
                f"[{m.scope.value}] ({m.source.value}): {m.content}"
                for m in items
            ]

        return {
            "user_command": user_command,
            "available_tools": tools_summary,
            "relevant_memories": relevant_memories,
            "workspace_root": str(settings.workspace_root),
            "free_disk_gb": resources.free_disk_gb,
            "offline_mode": settings.offline_mode
        }