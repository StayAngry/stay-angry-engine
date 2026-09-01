import pytest
from pathlib import Path
from sae.workspace import WorkspaceSandbox, SecurityViolationError


def test_valid_workspace_containment(tmp_path: Path):
    sandbox = WorkspaceSandbox(tmp_path)
    target = sandbox.validate_and_resolve_path("projects/sample.txt")
    assert target.is_relative_to(tmp_path)
    assert target == (tmp_path / "projects" / "sample.txt").resolve()


def test_escape_attempt_prevention(tmp_path: Path):
    sandbox = WorkspaceSandbox(tmp_path)
    with pytest.raises(SecurityViolationError):
        sandbox.validate_and_resolve_path("../../Windows/System32/calc.exe")


def test_absolute_path_outside_workspace_rejected(tmp_path: Path):
    sandbox = WorkspaceSandbox(tmp_path)
    outside_path = tmp_path.parent / "outside_file.txt"
    with pytest.raises(SecurityViolationError):
        sandbox.validate_and_resolve_path(outside_path)