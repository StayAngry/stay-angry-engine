"""Security sandbox for local workspace path containment on Windows/POSIX."""

import os
from pathlib import Path


class SecurityViolationError(Exception):
    pass


class WorkspaceSandbox:
    def __init__(self, root_path: Path):
        self.root_path = root_path.resolve()
        self.root_path.mkdir(parents=True, exist_ok=True)

    def validate_and_resolve_path(self, target_path: str | Path) -> Path:
        path_obj = Path(target_path)
        
        if path_obj.is_absolute():
            resolved = path_obj.resolve()
        else:
            resolved = (self.root_path / path_obj).resolve()

        try:
            resolved.relative_to(self.root_path)
        except ValueError:
            raise SecurityViolationError(
                f"Access denied: Target path '{target_path}' resolves to '{resolved}', outside workspace root '{self.root_path}'"
            )

        return resolved