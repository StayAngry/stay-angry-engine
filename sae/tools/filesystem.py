"""Foundational filesystem tools with sandbox security."""

import shutil
from typing import Any
from sae.permissions import PermissionLevel, RiskLevel
from sae.tools.base import BaseTool, ToolResult
from sae.verification import VerificationEngine
from sae.workspace import WorkspaceSandbox


class CreateDirectoryTool(BaseTool):
    name = "fs_create_directory"
    description = "Creates a directory inside the workspace."
    permission_level = PermissionLevel.CREATE
    risk_level = RiskLevel.LOW

    def __init__(self, sandbox: WorkspaceSandbox):
        self.sandbox = sandbox

    def validate_input(self, **kwargs: Any) -> bool:
        return "path" in kwargs and isinstance(kwargs["path"], str)

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            target_path = self.sandbox.validate_and_resolve_path(kwargs["path"])
            target_path.mkdir(parents=True, exist_ok=True)
            verification = VerificationEngine.verify_directory_exists(target_path)
            
            return ToolResult(
                success=(verification.status.value == "PASS"),
                data={"path": str(target_path)},
                verification=verification
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class WriteFileTool(BaseTool):
    name = "fs_write_file"
    description = "Writes text content to a file inside the workspace."
    permission_level = PermissionLevel.CREATE
    risk_level = RiskLevel.MEDIUM

    def __init__(self, sandbox: WorkspaceSandbox):
        self.sandbox = sandbox

    def validate_input(self, **kwargs: Any) -> bool:
        return "path" in kwargs and "content" in kwargs

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            target_path = self.sandbox.validate_and_resolve_path(kwargs["path"])
            content = str(kwargs.get("content", ""))
            
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content, encoding="utf-8")
            
            verification = VerificationEngine.verify_file_content(target_path, content)
            return ToolResult(
                success=(verification.status.value == "PASS"),
                data={"path": str(target_path), "bytes_written": len(content.encode("utf-8"))},
                verification=verification
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class ReadFileTool(BaseTool):
    name = "fs_read_file"
    description = "Reads text content from a file within the workspace."
    permission_level = PermissionLevel.READ
    risk_level = RiskLevel.LOW

    def __init__(self, sandbox: WorkspaceSandbox):
        self.sandbox = sandbox

    def validate_input(self, **kwargs: Any) -> bool:
        return "path" in kwargs

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            target_path = self.sandbox.validate_and_resolve_path(kwargs["path"])
            if not target_path.exists():
                return ToolResult(success=False, error=f"File not found: {kwargs['path']}")
            
            content = target_path.read_text(encoding="utf-8")
            return ToolResult(
                success=True,
                data={"path": str(target_path), "content": content}
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class DeletePathTool(BaseTool):
    name = "fs_delete_path"
    description = "Deletes a file or directory from the workspace."
    permission_level = PermissionLevel.DELETE
    risk_level = RiskLevel.HIGH

    def __init__(self, sandbox: WorkspaceSandbox):
        self.sandbox = sandbox

    def validate_input(self, **kwargs: Any) -> bool:
        return "path" in kwargs and isinstance(kwargs["path"], str)

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            target_path = self.sandbox.validate_and_resolve_path(kwargs["path"])
            if not target_path.exists():
                return ToolResult(success=True, data={"message": "Path did not exist."})
            
            if target_path.is_dir():
                shutil.rmtree(target_path)
            else:
                target_path.unlink()

            verification = VerificationEngine.verify_path_deleted(target_path)
            return ToolResult(
                success=(verification.status.value == "PASS"),
                data={"path": str(target_path)},
                verification=verification
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))